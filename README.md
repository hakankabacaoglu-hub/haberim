# Haberim

Personal news reader. GitHub Actions fetches the feeds in `scripts/feeds.json` every 2 hours
and publishes `site/` to GitHub Pages.

- Add or remove a source: edit `scripts/feeds.json`, commit. The site rebuilds automatically.
- Run an update now: Actions tab > "Update news" > Run workflow.
- A source that fails is listed under "Kaynak durumu" at the bottom of each tab.
