# shellcheck shell=bash
# Shared upload path for the two CI publish steps (specs-publish.sh).
#
# Why this file exists (issue #129): both steps uploaded ~25-40 small objects at *one file per
# second* — `mc cp --recursive` / `mc mirror` defaulted `--max-workers` to autodetect, which
# serialized against Garage where each PUT pays a 2-replica longhorn-bulk fsync. The lever is
# parallelism, NOT the endpoint: these scripts also run on the proxmox-vm runner where
# `garage.garage.svc` does not resolve, so the LAN default endpoint stays and only the workflow
# may switch SPECS_S3_ENDPOINT per job (never sniffed). Here we just pin an explicit, overridable
# concurrency so the same small-object set uploads in one parallel batch.
#
# S3_PUBLISH_WORKERS: concurrent object transfers per rclone invocation (--transfers). Default 32 clears today's
# object counts in ~one round; tune down if a run ever hammers Garage. Overridable via env only.
S3_PUBLISH_WORKERS="${S3_PUBLISH_WORKERS:-32}"

# (mc/minio-client is insecure+abandoned in nixpkgs — issue #135 — so this is rclone now.)

# s3_publish_alias <name> <endpoint> <access-key> <secret-key>
# Define the rclone remote <name> via RCLONE_CONFIG_<NAME>_* env vars — no config file and no
# secrets in argv. Exported into the caller's shell, so call it directly (not in a subshell).
# Garage signs SigV4 with region `garage` (rclone's default us-east-1 → AuthorizationHeaderMalformed,
# PR #148); NO_CHECK_BUCKET stops rclone trying CreateBucket on an existing bucket.
s3_publish_alias() {
  local up
  up="$(printf '%s' "$1" | tr '[:lower:]-' '[:upper:]_')"
  export "RCLONE_CONFIG_${up}_TYPE=s3" "RCLONE_CONFIG_${up}_PROVIDER=Other" \
    "RCLONE_CONFIG_${up}_ENDPOINT=$2" "RCLONE_CONFIG_${up}_ACCESS_KEY_ID=$3" \
    "RCLONE_CONFIG_${up}_SECRET_ACCESS_KEY=$4" "RCLONE_CONFIG_${up}_FORCE_PATH_STYLE=true" \
    "RCLONE_CONFIG_${up}_REGION=${S3_PUBLISH_REGION:-garage}" "RCLONE_CONFIG_${up}_NO_CHECK_BUCKET=true"
}

# s3_publish_cp <src-dir> <remote:bucket/path>
# Parallel upload of a whole local directory (the allure report/svg/e2e trees). rclone's
# non-zero exit on any failed transfer propagates (oracle-fleet#318: the old client exited 0 on rejected PUTs).
s3_publish_cp() {
  rclone copy --transfers "$S3_PUBLISH_WORKERS" "$1" "$2"
}

# s3_publish_mirror <src> <remote:bucket/path>      → additive (rclone copy; never deletes)
# s3_publish_mirror --remove <src> <dest>           → exact mirror (rclone sync; deletes extras)
s3_publish_mirror() {
  local verb=copy
  if [ "${1:-}" = "--remove" ]; then verb=sync; shift; fi
  rclone "$verb" --transfers "$S3_PUBLISH_WORKERS" "$@"
}
