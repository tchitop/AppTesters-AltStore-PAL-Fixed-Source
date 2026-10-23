# AppTesters PAL filter

This project fetches `https://repository.apptesters.org/`, filters the source conservatively, and publishes `source.json`, a validation report, and a small website with GitHub Pages.

**It does not create/fake marketplace IDs or notarize apps.** AltStore PAL needs a real Apple marketplace ID and the official Alternative Distribution Package (ADP). A regular `.ipa` link cannot be made PAL-compatible by editing JSON.

## Install
1. Create a public GitHub repository and upload these files to its default branch.
2. In **Settings → Pages**, select **GitHub Actions** as the build source.
3. Open **Actions → Sync and validate AppTesters source → Run workflow**.
4. After it succeeds, open the Pages site. It displays the `source.json` URL and validation report.
5. Add that URL in AltStore PAL → Sources → +.

The workflow also runs daily. It mirrors source metadata only, not IPA binaries.

## Filtering rules
An app must have `name`, `bundleIdentifier`, `developerName`, and a non-empty `marketplaceID`, plus at least one version with required version metadata and a `downloadURL` ending in `manifest.json`. The script never guesses missing data.

A zero-app result means the upstream is probably a traditional IPA source, not a PAL ADP source. The report checks metadata and URL shape only; it cannot independently prove notarization or validate ADP signatures.
