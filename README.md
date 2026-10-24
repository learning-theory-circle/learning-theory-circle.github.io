# Learning Theory Circle

We are a community of students and researchers who share a passion for the theory of learning. This is our website for a biweekly event on the this subject, built with [Jekyll](https://jekyllrb.com/) and the default **minima** theme, hosted on GitHub Pages.


## Add a Talk Entry

Edit **`_data/talks.yml`** and add one entry. See the comments at the top of that file for all available fields. Its content should look like below. Note that `id` is the name of the presenter followed by the talk date.

```yaml
- date: 2026-08-19                               # required
  id: jane-doe-2026-aug-19                       # required
  presenter: Jane Doe                            # required
  presenter_url: https://example.com/jane-doe    # optional
  affiliation: Some University                   # optional
  title: "A Great Paper Title"                   # requried
  session: "1"                                   # optional
  paper: https://example.com/paper               # optional
  notes: https://example.com/notes               # optional
  book: https://example.com/book                 # optional
  authors: Doe, Smith                            # optional
  poster: /assets/posters/2026-08-19.png         # optional
  slides: /assets/slides/2026-08-19.pdf          # optional
  video: https://youtu.be/XXXXXXX                # optional
  abstract: "One or two sentences."              # required
```

The site sorts by `date` and splits entries into **Upcoming** and **Past** automatically. To host slides in the repository, drop the PDF in `assets/slides/` and point the `slides` field at it. To host a poster, drop the image or PDF in `assets/posters/` and point the `poster` field at it.


## Add the Talk Page

Each talk also gets its own page. The page shows the presenter, date, session number, full abstract, and all material links. Create `_pages/talks/<talk_id>.md`, where the file name `<talk_id>` must equal the `id` field of the talk entry you just added. The minimal content of this file should look like below. You can add extra information too.

```yaml
---
layout: talk
talk_id: jane-doe-2026-aug-19
nav_exclude: true
---
```


## Seminar Bot

A GitHub Actions job (`.github/workflows/seminar-bot.yml`) runs every day at 09:00 Tehran time. It reads `_data/talks.yml` and opens issues for the organizer set in `.github/seminar-bot/config.yml`:

- 14 days before a session with no talk: asks for the talk data, with reminders on days 11, 9, and 7.
- 7 days before: the announcement email and the Telegram text.
- 1 day before: the reminder email and the Telegram text.
- 2 days after a session with no `video`: asks for the video, with a reminder 3 days before the next session.

Issues close automatically when the data appears in `_data/talks.yml`. To add a talk, use the **New talk** issue form. The `new-talk.yml` workflow turns it into a pull request with previews of all texts; merge it to publish. The text templates are in `.github/seminar-bot/templates/`. To test the bot, run the workflow by hand from the Actions tab with **dry run** on, or locally:

```bash
python3 .github/seminar-bot/bot.py run --dry-run --today 2026-11-01
python3 .github/seminar-bot/bot.py preview <talk_id>
```


## Run Locally

To run the site locally, you need `ruby` and `bundler`. After running the following commands, open <http://localhost:4000>.

```bash
bundle install
bundle exec jekyll serve
```
