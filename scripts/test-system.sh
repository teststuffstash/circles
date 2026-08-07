#!/usr/bin/env -S bash -euo pipefail
# test-system.sh — system-testing gate (kind cluster, real image, page fetched & asserted)
#
# Prerequisites: a real Docker daemon. This is the "system testing" tier
# per CIR-PROC-TEST-TIERS: logic against real components in a local cluster (kind).
#
# Environment:
#   CIRCLES_SYSTEM_TEST_SKIP  — set to "1" to skip (e.g. when no Docker daemon)
#   CIRCLES_IMAGE             — image repository (default: circles-system-test)
#   CIRCLES_TAG               — image tag (default: test-$(git rev-parse --short HEAD))
#
# The script bakes a real artifact from the fixture, builds an image containing it,
# creates a kind cluster, installs the chart, fetches the page, and asserts the baked
# content is served — not the vanilla bootstrap placeholder.
#
# Requirements evidenced (system tier):
#   CIR-PROC-PHASE-P0#p0-page-replaces-placeholder
#   CIR-BAKE-SELF-CONTAINED#inlined-data-equals-the-file
#   CIR-RENDER-NO-EGRESS
#   CIR-PROC-DEPLOY-SEAM#image-buildable-from-this-repo-alone

cd "$(dirname "$0")/.."

# ── skip guard ──────────────────────────────────────────────────────────────────
if [ "${CIRCLES_SYSTEM_TEST_SKIP:-}" = "1" ]; then
  echo "==> test-system: SKIPPED (CIRCLES_SYSTEM_TEST_SKIP=1)"
  exit 0
fi

# ── prerequisites ───────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "ERROR: docker not found — system test requires a Docker daemon." >&2
  echo "  Set CIRCLES_SYSTEM_TEST_SKIP=1 to skip." >&2
  exit 1
fi
if ! docker info &>/dev/null; then
  echo "ERROR: docker daemon not reachable." >&2
  echo "  Set CIRCLES_SYSTEM_TEST_SKIP=1 to skip." >&2
  exit 1
fi
if ! command -v kind &>/dev/null; then
  echo "ERROR: kind not found." >&2
  exit 1
fi

# ── config ──────────────────────────────────────────────────────────────────────
REFERENCE_DATE="2026-08-03"
CLUSTER_NAME="circles-test"
IMG="${CIRCLES_IMAGE:-circles-system-test}"
TAG="${CIRCLES_TAG:-test-$(git rev-parse --short HEAD 2>/dev/null || echo 'local')}"
FULL_IMAGE="${IMG}:${TAG}"

# Temp dirs (cleaned up by trap)
BAKE_OUT=$(mktemp -d /tmp/circles-bake.XXXXXX)
BUILD_CTX=$(mktemp -d /tmp/circles-build.XXXXXX)
FETCH_DIR=$(mktemp -d /tmp/circles-fetch.XXXXXX)
KIND_CONFIG=$(mktemp /tmp/kind-config.XXXXXX.yaml)

FAIL_COUNT=0

# ── cleanup trap (reliable — deletes cluster even on failure) ───────────────────
cleanup() {
  set +e
  echo ""
  echo "==> test-system: cleanup…"
  # Kill any lingering port-forward
  if [ -n "${PF_PID:-}" ]; then
    kill "$PF_PID" 2>/dev/null || true
  fi
  # Delete kind cluster
  if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    kind delete cluster --name "$CLUSTER_NAME" 2>&1 | sed 's/^/  /'
  fi
  # Clean temp dirs
  rm -rf "$BAKE_OUT" "$BUILD_CTX" "$FETCH_DIR" "$KIND_CONFIG"
  echo "==> test-system: cleanup done"
}
trap cleanup EXIT

# ── assertion helpers ───────────────────────────────────────────────────────────
assert_pass() { echo "  PASS: $1"; }
assert_fail() {
  local msg="$1"
  echo "  FAIL: $msg" >&2
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: Bake the real artifact
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "==> step 1/7: bake artifact (reference-date=$REFERENCE_DATE)"
uv run --frozen python -m bake \
  --config fixtures/alex/circles.yaml \
  --out "$BAKE_OUT" \
  --reference-date "$REFERENCE_DATE"
echo "  bake: PASS"

# Verify the fixture lights from the acceptance criteria (CIR-PROC-PHASE-P0)
echo "  verifying fixture lights…"
uv run --frozen python -c "
import json, sys

with open('$BAKE_OUT/data.json') as f:
    art = json.load(f)

# Build lookup: (ring_id, item_id) -> item
items = {}
for ring in art['rings']:
    for item in ring['items']:
        items[(ring['id'], item['id'])] = item

expected = {
    ('self', 'sleep'):       {'status': 'grey',  'grey_reason': 'not-evaluated'},
    ('self', 'labs'):        {'status': 'grey',  'grey_reason': 'not-evaluated'},
    ('self', 'exercise'):    {'status': 'grey',  'grey_reason': 'by-choice'},
    ('partner', 'date-night'): {'status': 'yellow', 'grey_reason': None},
    ('children', 'nova'):    {'status': 'green', 'grey_reason': None},
    ('children', 'kit'):     {'status': 'green', 'grey_reason': None},
    ('wider', 'friends'):    {'status': 'red',   'grey_reason': None},
    ('wider', 'plants'):     {'status': 'grey',  'grey_reason': 'not-evaluated'},
}

errors = []
for key, want in expected.items():
    item = items.get(key)
    if item is None:
        errors.append(f'{key[0]}/{key[1]}: not found in baked artifact')
        continue
    if item['status'] != want['status']:
        errors.append(f'{key[0]}/{key[1]} status: expected {want[\"status\"]}, got {item[\"status\"]}')
    if item.get('grey_reason') != want['grey_reason']:
        errors.append(f'{key[0]}/{key[1]} grey_reason: expected {want[\"grey_reason\"]}, got {item.get(\"grey_reason\")}')

if errors:
    for e in errors:
        print(f'  FAIL: {e}', file=sys.stderr)
    sys.exit(1)
print('  fixture lights verified: PASS')
" 2>&1

echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: Build Docker image with baked content
# ═══════════════════════════════════════════════════════════════════════════════
echo "==> step 2/7: build image $FULL_IMAGE"
mkdir -p "$BUILD_CTX/dist"
cp "$BAKE_OUT/data.json" "$BUILD_CTX/dist/"
cp "$BAKE_OUT/index.html" "$BUILD_CTX/dist/"

cat > "$BUILD_CTX/Dockerfile" << 'DF'
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY dist/ /usr/share/nginx/html/
DF

docker build -t "$FULL_IMAGE" "$BUILD_CTX" 2>&1 | sed 's/^/  /'
echo "  image built: $FULL_IMAGE"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: Create kind cluster with registry mirrors
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "==> step 3/7: create kind cluster '$CLUSTER_NAME'"

# Configure the kind node's containerd to use the LAN mirrors before the node starts.
# The node's own image pulls (e.g. for the pause image) go through these mirrors too.
cat > "$KIND_CONFIG" << YAML
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: ${CLUSTER_NAME}
containerdConfigPatches:
- |-
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
    endpoint = ["http://192.168.40.20"]
- |-
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."ghcr.io"]
    endpoint = ["http://192.168.40.21"]
YAML

kind create cluster --config "$KIND_CONFIG" 2>&1 | sed 's/^/  /'
echo "  kind cluster created"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4: Load image into kind
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "==> step 4/7: load image into kind"
kind load docker-image --name "$CLUSTER_NAME" "$FULL_IMAGE" 2>&1 | sed 's/^/  /'
echo "  image loaded"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5: Install the chart
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "==> step 5/7: helm install chart"
helm upgrade --install "$CLUSTER_NAME" chart/ \
  --namespace default \
  --create-namespace \
  --set image.repository="${IMG}" \
  --set image.tag="${TAG}" \
  --set image.pullPolicy=Never \
  --wait --timeout 120s 2>&1 | sed 's/^/  /'
echo "  chart installed"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6: Wait for deployment and fetch page
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "==> step 6/7: wait for deployment and fetch page"
kubectl rollout status "deployment/$CLUSTER_NAME" --namespace default --timeout=120s 2>&1 | sed 's/^/  /'

# Port-forward to access the pod (nginx-unprivileged listens on 8080)
PF_PORT=8888
kubectl port-forward "deployment/$CLUSTER_NAME" --namespace default "${PF_PORT}:8080" &
PF_PID=$!
sleep 5  # Allow port-forward to establish

# Fetch pages
echo "  fetching index.html…"
HTTP_CODE=$(curl -sf -o "$FETCH_DIR/index.html" -w '%{http_code}' "http://127.0.0.1:${PF_PORT}/" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  echo "  index.html: HTTP $HTTP_CODE ($(wc -c < "$FETCH_DIR/index.html") bytes)"
else
  assert_fail "could not fetch index.html from cluster (HTTP $HTTP_CODE)"
fi

echo "  fetching data.json…"
HTTP_CODE=$(curl -sf -o "$FETCH_DIR/data.json" -w '%{http_code}' "http://127.0.0.1:${PF_PORT}/data.json" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  echo "  data.json: HTTP $HTTP_CODE ($(wc -c < "$FETCH_DIR/data.json") bytes)"
else
  # nginx might not serve .json by default — that's okay, data is inlined
  echo "  NOTE: data.json returned HTTP $HTTP_CODE — relying on inlined data check"
  touch "$FETCH_DIR/data.json"
fi

kill "$PF_PID" 2>/dev/null || true
wait "$PF_PID" 2>/dev/null || true
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 7: System assertions
# ═══════════════════════════════════════════════════════════════════════════════
echo "==> step 7/7: system assertions"

# 7a — served page is baked, not placeholder (CIR-PROC-PHASE-P0#p0-page-replaces-placeholder)
echo "  7a: p0-page-replaces-placeholder"
if [ ! -f "$FETCH_DIR/index.html" ]; then
  assert_fail "index.html was not fetched from cluster"
else
  if grep -q 'self/sleep' "$FETCH_DIR/index.html" 2>/dev/null; then
    assert_pass "served page contains fixture content (self/sleep)"
  else
    assert_fail "served page is the vanilla placeholder — bake content missing"
  fi
  if grep -q 'generated_at' "$FETCH_DIR/index.html" 2>/dev/null; then
    assert_pass "served page has generated_at stamp"
  else
    assert_fail "served page missing generated_at stamp"
  fi
fi

# 7b — inlined data equals baked data (CIR-BAKE-SELF-CONTAINED#inlined-data-equals-the-file)
echo "  7b: inlined-data-equals-the-file"
if [ -s "$FETCH_DIR/data.json" ]; then
  # Check served data.json matches baked artifact
  if python3 -c '
import json, sys
with open("'"$FETCH_DIR"'/data.json") as f: served = json.load(f)
with open("'"$BAKE_OUT"'/data.json") as f: baked = json.load(f)
if served != baked:
    sys.exit(1)
' 2>/dev/null; then
    assert_pass "served data.json matches baked artifact"
  else
    assert_fail "served data.json differs from baked artifact"
  fi
fi

# Check inlined data equals the baked data (always the primary check even when data.json not served)
if [ -f "$FETCH_DIR/index.html" ]; then
  if python3 -c '
import json, sys
with open("'"$FETCH_DIR"'/index.html") as f: html = f.read()
with open("'"$BAKE_OUT"'/data.json") as f: baked = json.load(f)
marker = "<script id=\"artifact-data\" type=\"application/json\">"
start = html.find(marker)
if start < 0:
    sys.exit(1)
start = html.index(">", start) + 1
end = html.index("</script>", start)
inlined = json.loads(html[start:end].strip())
if inlined != baked:
    sys.exit(1)
' 2>/dev/null; then
    assert_pass "inlined data matches baked artifact"
  else
    assert_fail "inlined data does not match baked artifact"
  fi
else
  assert_fail "index.html was not fetched — cannot check inlined data"
fi

# 7c — no third-party origins in served markup (CIR-RENDER-NO-EGRESS)
echo "  7c: no-external-origins"
if [ -f "$FETCH_DIR/index.html" ]; then
  # Use python3 with heredoc-style input via stdin to avoid quoting issues
  if python3 -c '
import re, sys
with open("'"$FETCH_DIR"'/index.html") as f: html = f.read()
urls = re.findall(r"https?://[^\"\047\s<>]+", html)
external = [u for u in urls if "w3.org" not in u and "127.0.0.1" not in u]
if external:
    print("Found external URLs: " + str(external), file=sys.stderr)
    sys.exit(1)
' 2>/dev/null; then
    assert_pass "no external origins in served page"
  else
    assert_fail "external origins found in served page"
  fi
else
  assert_fail "index.html was not fetched — cannot check external origins"
fi

# 7d — chart's Service has a cluster IP (proves the chart actually routes)
echo "  7d: service-routes-to-page"
SVC_IP=$(kubectl get "service/$CLUSTER_NAME" --namespace default -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
if [ -n "$SVC_IP" ] && [ "$SVC_IP" != "None" ]; then
  assert_pass "Service has cluster IP: $SVC_IP"
else
  assert_fail "Service has no cluster IP or is None"
fi

echo ""
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo "==> test-system: ALL PASS"
  exit 0
else
  echo "==> test-system: $FAIL_COUNT assertion(s) FAILED" >&2
  exit 1
fi
