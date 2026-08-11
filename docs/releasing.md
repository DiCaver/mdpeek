# Releasing MDPeek

MDPeek uses `mdpeek/version.py` as its authoritative version. The release workflow validates the `v`-prefixed Git tag against it and never rewrites source from a tag.

1. Update the version source and release notes.
2. Run all tests.
3. Build locally, or inspect the downloadable Windows workflow artifact.
4. Test the installer and portable build, including paths with spaces and Unicode.
5. Commit the reviewed release changes.
6. Create the matching tag, for example `git tag v0.1.0`.
7. Push that tag with `git push origin v0.1.0`.
8. Inspect the draft GitHub release created by the tag workflow.
9. Download and test its final installer, ZIP, and checksums on a clean Windows x64 machine.
10. Publish the release manually after approval.

The tag workflow has write permission only for its release job. It runs tests, validates the version, builds both editions from the same PyInstaller directory, generates checksums from the final files, uploads a retained workflow artifact, and creates a draft release. Ordinary pushes and pull requests only validate and retain a smoke build.

Do not publish an unsigned artifact from anywhere other than the official repository. Do not add self-signed code signing; add signing only when a legitimate certificate is explicitly authorized.
