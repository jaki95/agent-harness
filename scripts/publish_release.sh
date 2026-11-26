#!/usr/bin/env bash
set -euo pipefail

die() { echo "$*" >&2; exit 1; }

[[ $# == 3 ]] || die "Usage: publish_release.sh VERSION SHA NOTES_FILE"
version=$1
sha=$2
notes=$3
: "${GH_REPO:?Set GH_REPO to the release repository}"
[[ $version =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] || die "Invalid release version: $version"
head=$(git rev-parse --verify 'HEAD^{commit}')
[[ $sha == "$head" ]] || die "The checked-out commit must match the full release SHA: $sha"
[[ -f $notes && -r $notes && -s $notes ]] || die "Missing or empty release notes: $notes"
ref="refs/tags/$version"

remote_target() {
    git ls-remote --tags origin "$ref" "$ref^{}" |
        awk -v ref="$ref" '$2 == ref { tag = $1 } $2 == ref "^{}" { peeled = $1 }
                           END { print (peeled ? peeled : tag) }'
}

release_state() {
    # With contents:write, the list includes drafts even when the tag has no public release.
    gh api --paginate "repos/$GH_REPO/releases?per_page=100" --jq \
        ".[] | select(.tag_name == \"$version\") | [.draft, .prerelease] | @tsv"
}

target=$(remote_target)
[[ -z $target || $target == "$sha" ]] || die "$version already points to a different commit: $target"
state=$(release_state)
if [[ -n $state ]]; then
    [[ $state == $'false\tfalse' ]] || die "An existing draft, prerelease or ambiguous record needs review: $version"
else
    if [[ -z $target ]]; then
        git push --no-follow-tags origin "$sha:$ref" || echo "Tag push unconfirmed; checking origin." >&2
        target=$(remote_target)
        [[ $target == "$sha" ]] || die "Origin did not confirm $version at $sha"
    fi
    gh release create "$version" --repo "$GH_REPO" --verify-tag --title "$version" --notes-file "$notes" ||
        echo "Release creation unconfirmed; checking GitHub." >&2
    state=$(release_state)
    [[ $state == $'false\tfalse' ]] || die "GitHub did not confirm a published stable release for $version"
fi
target=$(remote_target)
[[ $target == "$sha" ]] || die "Publication could not confirm $version at $sha on origin"
echo "$version is published at $sha"
