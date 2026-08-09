# Learning Theory Circle

Website for a biweekly event on the theory of learning, built with [Jekyll](https://jekyllrb.com/) and the default **minima** theme, hosted on GitHub Pages.


## Add a talk

Edit **`_data/talks.yml`** and add one entry (see the comments at the top of that file for all available fields):

```yaml
- date: 2026-08-19
  presenter: Jane Doe
  presenter_url: https://example.com/jane-doe    # optional
  affiliation: Some University
  title: "A Great Paper Title"
  paper: https://arxiv.org/abs/xxxx.xxxxx
  authors: Doe, Smith
  poster: /assets/posters/2026-08-19.png         # optional
  slides: /assets/slides/2026-08-19.pdf          # optional
  video: https://youtu.be/XXXXXXX                # optional
  abstract: "One or two sentences."              # optional
```

The site sorts by `date` and splits entries into **Upcoming** and **Past** automatically. To host slides in the repo, drop the PDF in `assets/slides/` and point `slides:` at it. To host a poster, drop the image or PDF in `assets/posters/` and point `poster:` at it.


## Fill in before launch

Open `_config.yml` and set these (leave any of them `""` to hide that element):

- `contact_email` — organizer / group email
- `organizers` — names to show on the site; use `name` and `url` for hyperlinks
- `mailing_list_url` — e.g. a Google Group for announcements
- `youtube_playlist_url` — where recordings live
- `calendar_embed_url` — the `src` URL from Google Calendar's *Embed code*

Then edit **`about.md`** to set the day/time/timezone and location, and replace the placeholder talks in `_data/talks.yml`.


## Set up the Google Calendar + Meet link

1. In [Google Calendar](https://calendar.google.com), create a new calendar (left sidebar → **Other calendars → +** → *Create new calendar*), e.g. "Learning Theory Circle".

2. Create a biweekly event: title it, set **Sunday 7:00 pm**, timezone **(GMT+3:30) Tehran**, and under *Does not repeat* choose *custom* and set repeat every two weeks. Click **Add Google Meet video conferencing** — a recurring event keeps the **same Meet link** every two weeks. Copy that link into `meet_url` in `_config.yml`.

3. Make the calendar public so visitors can see it: calendar **Settings → Access permissions → Make available to public**.

4. Get the embed URL: calendar **Settings → Integrate calendar → Embed code**. Copy the `src="..."` value into `calendar_embed_url` in `_config.yml`. To force Tehran time for all viewers, make sure the URL ends with `&ctz=Asia/Tehran`.


## Run locally

Requires `ruby` and `bundler`.

```bash
bundle install
bundle exec jekyll serve
```

Open <http://localhost:4000>.
