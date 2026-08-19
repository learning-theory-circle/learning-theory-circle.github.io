# Learning Theory Circle

We are a community of students and researchers who share a passion for the theory of learning. This is our website for a biweekly event on the this subject, built with [Jekyll](https://jekyllrb.com/) and the default **minima** theme, hosted on GitHub Pages.


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

The site sorts by `date` and splits entries into **Upcoming** and **Past** automatically. To host slides in the repository, drop the PDF in `assets/slides/` and point the `slides` field at it. To host a poster, drop the image or PDF in `assets/posters/` and point the `poster` field at it.


## Run locally

To run the site locally, you need `ruby` and `bundler`. After running the following commands, open <http://localhost:4000>.

```bash
bundle install
bundle exec jekyll serve
```
