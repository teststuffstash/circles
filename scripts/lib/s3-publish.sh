# shellcheck shell=bash
# Shared upload path for the two CI publish steps (specs-publish.sh).
#
# Why this file exists (issue #129): both steps uploaded ~25-40 small objects at *one file per
# second* — `mc cp --recursive` / `mc mirror` default `--max-workers` to autodetect, which
# serialized against Garage where each PUT pays a 2-replica longhorn-bulk fsync. The lever is
# parallelism, NOT the endpoint: these scripts also run on the proxmox-vm runner where
# `garage.garage.svc` does not resolve, so the LAN default endpoint stays and only the workflow
# may switch SPECS_S3_ENDPOINT per job (never sniffed). Here we just pin an explicit, overridable
# concurrency so the same small-object set uploads in one parallel batch.
#
# S3_PUBLISH_WORKERS: concurrent object transfers per mc invocation. Default 32 clears today's
# object counts in ~one round; tune down if a run ever hammers Garage. Overridable via env only.
S3_PUBLISH_WORKERS="${S3_PUBLISH_WORKERS:-32}"

# s3_publish_alias <alias> <endpoint> <access-key> <secret-key>
# Register the mc alias the upload helpers target (thin wrapper — kept here so both scripts share
# the one definition and the alias name never drifts between them).
s3_publish_alias() {
  mc alias set "$1" "$2" "$3" "$4" >/dev/null
}

# s3_publish_cp <src-dir> <dest>
# Recursive, parallel upload of a whole local directory (the allure report/svg/e2e trees).
s3_publish_cp() {
  mc cp --quiet --recursive --max-workers "$S3_PUBLISH_WORKERS" "$1" "$2"
}

# s3_publish_mirror [mc-mirror-flags...] <src> <dest>
# Parallel mirror (the specs site). Extra flags (--overwrite, --remove) pass through verbatim.
s3_publish_mirror() {
  mc mirror --quiet --max-workers "$S3_PUBLISH_WORKERS" "$@"
}
