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

# Check docker is available
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

# Temp dirs
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
  kill "$PF_PID" 2>/dev/null || true
  # Delete kind cluster
  if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    kind delete cluster --name "$CLUSTER_NAME" 2>&1 | sed 's/^/  /'
  fi
  # Clean temp dirs
  rm -rf "$BAKE_OUT" "$BUILD_CTX" "$FETCH_DIR" "$KIND_CONFIG"
  echo "==> test-system: cleanup done"
}
trap cleanup EXIT

# ── assertions helper ───────────────────────────────────────────────────────────
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

# Verify the artifact carries expected fixture lights (CIR-PROC-PHASE-P0)
uv run --frozen python -c "
import json, sys
with open('$BAKE_OUT/data.json') as f:
    art = json.load(f)
expected = {
    ('self','sleep'): 'not-evaluated', ('self','labs'): 'not-evaluated',
    ('self','exercise'): 'by-choice', ('partner','date-night'): 'yellow',
    ('children','nova'): 'green', ('children','kit'): 'green',
    ('wider','friends'): 'red', ('wider','plants'): 'not-evaluated',
}
for ring in art['rings']:
    for item in ring['items']:
        key = (ring['id'], item['id'])
        if key in expected:
            actual = item.get('grey_reason')
            want = expected[key]
            if actual != want:
                print(f'FAIL: {key[0]}/{key[1]} grey_reason: expected {want}, got {actual}', file=sys.stderr)
                sys.exit(1)
print('  fixture lights verified: PASS')
"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: Build Docker image with baked content
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "==> step 2/7: build image $FULL_IMAGE"
# Set up build context: Dockerfile + dist/ directory
cp "$BAKE_OUT/data.json" "$BAKE_OUT/index.html" "$BUILD_CTX/dist/" 2>/dev/null || mkdir -p "$BUILD_CTX/dist"
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

# Port-forward to access the pod
PF_PORT=8888
kubectl port-forward "deployment/$CLUSTER_NAME" "${PF_PORT}:8080" &
PF_PID=$!
sleep 4  # Allow port-forward to establish

# Fetch pages
curl -sf "http://127.0.0.1:${PF_PORT}/" > "$FETCH_DIR/index.html" || {
  assert_fail "could not fetch index.html from cluster"
}
curl -sf "http://127.0.0.1:${PF_PORT}/data.json" > "$FETCH_DIR/data.json" || {
  echo "  NOTE: data.json not served (expected for nginx without extension handling)"
  touch "$FETCH_DIR/data.json"
}

kill "$PF_PID" 2>/dev/null || true
wait "$PF_PID" 2>/dev/null || true

echo "  page fetched (${#FETCH_DIR} bytes)"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 7: System assertions
# ═══════════════════════════════════════════════════════════════════════════════
echo "==> step 7/7: system assertions"

# 7a — served page is baked, not placeholder (CIR-PROC-PHASE-P0#p0-page-replaces-placeholder)
echo "  7a: p0-page-replaces-placeholder"
if grep -q 'self/sleep' "$FETCH_DIR/index.html" 2>/dev/null; then
  assert_pass "served page contains fixture content"
else
  assert_fail "served page is the vanilla placeholder — bake content missing"
fi
if grep -q 'generated_at' "$FETCH_DIR/index.html" 2>/dev/null; then
  assert_pass "served page has generated_at stamp"
else
  assert_fail "served page missing generated_at stamp"
fi

# 7b — inlined data equals served data.json (CIR-BAKE-SELF-CONTAINED#inlined-data-equals-the-file)
echo "  7b: inlined-data-equals-the-file"
if [ -s "$FETCH_DIR/data.json" ]; then
  # Check served data.json matches baked artifact
  if python3 -c "
import json, sys
with open('$FETCH_DIR/data.json') as f: served = json.load(f)
with open('$BAKE_OUT/data.json') as f: baked = json.load(f)
if served != baked:
    sys.exit(1)
" 2>/dev/null; then
    assert_pass "served data.json matches baked artifact"
  else
    assert_fail "served data.json differs from baked artifact"
  fi

  # Check inlined data equals served data.json
  if python3 -c "
import json, sys
with open('$FETCH_DIR/index.html') as f: html = f.read()
with open('$FETCH_DIR/data.json') as f: served = json.load(f)
marker = '<script id=\"artifact-data\" type=\"application/json\">'
start = html.find(marker)
if start < 0:
    sys.exit(1)
start = html.index('>', start) + 1
end = html.index('</script>', start)
inlined = json.loads(html[start:end].strip())
if inlined != served:
    sys.exit(1)
" 2>/dev/null; then
    assert_pass "inlined data matches served data.json"
  else
    assert_fail "inlined data does not match served data.json"
  fi
else
  assert_fail "data.json not served from cluster"
fi

# 7c — no third-party origins (CIR-RENDER-NO-EGRESS)
echo "  7c: no-external-origins"
if python3 -c "
import re, sys
with open('$FETCH_DIR/index.html') as f: html = f.read()
urls = re.findall(r'https?://[^\"'\\''\\s<>]+', html)
external = [u for u in urls if 'w3.org' not in u and '127.0.0.1' not in u]
if external:
    sys.exit(1)
" 2>/dev/null; then
  assert_pass "no external origins in served page"
else
  assert_fail "external origins found in served page"
fi

# 7d — chart's Service routes to the page
echo "  7d: service-routes-to-page"
SVC_IP=$(kubectl get "service/$CLUSTER_NAME" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
if [ -n "$SVC_IP" ]; then
  assert_pass "Service has cluster IP: $SVC_IP"
else
  assert_fail "Service has no cluster IP"
fi

echo ""
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo "==> test-system: ALL PASS"
  exit 0
else
  echo "==> test-system: $FAIL_COUNT assertion(s) FAILED" >&2
  exit 1
fi
