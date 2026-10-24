"""Seminar bot for the Learning Theory Circle.

Commands:
  run       Daily task. Opens, comments on, and closes reminder issues.
  preview   Prints the emails and Telegram texts of one talk as Markdown.
  add-talk  Reads a "New talk" issue form and writes the talk entry and page.

The data comes from _data/talks.yml and _data/circle.yml. The bot never sends
email itself: it puts the texts in issues that are assigned to the organizer.
"""

import argparse
import datetime as dt
import json
import os
import re
import string
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

BOT_DIR = Path(__file__).resolve().parent
ROOT = BOT_DIR.parents[1]
TALKS_FILE = ROOT / "_data" / "talks.yml"
PAGES_DIR = ROOT / "_pages" / "talks"

BOT_LABEL = "seminar-bot"
NEW_TALK_LABEL = "new-talk"
MARKER = "<!-- seminar-bot:{} -->"

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
FA_WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
JALALI_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                 "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
GREGORIAN_MONTHS_FA = ["ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن",
                       "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"]

# (field id in talks.yml, label in .github/ISSUE_TEMPLATE/new-talk.yml)
FORM_FIELDS = [
    ("date", "Date"),
    ("presenter", "Presenter"),
    ("presenter_url", "Presenter webpage"),
    ("affiliation", "Affiliation"),
    ("title", "Title"),
    ("session", "Session"),
    ("paper", "Paper"),
    ("book", "Book"),
    ("notes", "Notes"),
    ("slides", "Slides"),
    ("poster", "Poster"),
    ("abstract", "Abstract"),
    ("side_notes", "Side notes"),
]
TALK_KEYS = ["date", "id", "presenter", "presenter_url", "affiliation", "title",
             "session", "paper", "book", "notes", "slides", "poster", "abstract"]


# ---------------------------------------------------------------- data

def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config():
    return load_yaml(BOT_DIR / "config.yml")


def load_circle():
    return load_yaml(ROOT / "_data" / "circle.yml")


def load_talks():
    return load_yaml(TALKS_FILE) or []


def next_session(today, cfg):
    """Return the first session date on or after `today`."""
    cadence = cfg["cadence_days"]
    days = (today - cfg["anchor_date"]).days
    return cfg["anchor_date"] + dt.timedelta(days=-(-days // cadence) * cadence)


def talk_on(talks, date):
    return next((t for t in talks if t["date"] == date), None)


def talk_before(talks, date):
    past = [t for t in talks if t["date"] < date]
    return max(past, key=lambda t: t["date"]) if past else None


# ---------------------------------------------------------------- texts

def to_jalali(d):
    g_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = d.year + 1 if d.month > 2 else d.year
    days = (355666 + 365 * d.year + (gy2 + 3) // 4 - (gy2 + 99) // 100
            + (gy2 + 399) // 400 + d.day + g_days[d.month - 1])
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        return jy, 1 + days // 31, 1 + days % 31
    return jy, 7 + (days - 186) // 30, 1 + (days - 186) % 30


def date_fa(d):
    _, jm, jd = to_jalali(d)
    text = (f"{FA_WEEKDAYS[d.weekday()]} {jd} {JALALI_MONTHS[jm - 1]} "
            f"({d.day} {GREGORIAN_MONTHS_FA[d.month - 1]})")
    return text.translate(FA_DIGITS)


def absolute_url(url, site_url):
    return site_url + url if url.startswith("/") else url


def talk_url(talk, site_url):
    return f"{site_url}/talks/{talk['id']}"


def template_values(talk, cfg, circle, site_url):
    presenter_line = talk["presenter"]
    if talk.get("affiliation"):
        presenter_line += f", {talk['affiliation']}"
    if talk.get("presenter_url"):
        presenter_line += f" ({talk['presenter_url']})"
    resources = [("Talk page", talk_url(talk, site_url))]
    for key in ["paper", "book", "notes", "slides"]:
        if talk.get(key):
            resources.append((key.capitalize(), absolute_url(talk[key], site_url)))
    session = str(talk.get("session") or "")
    return {
        "title": talk["title"],
        "presenter": talk["presenter"],
        "presenter_line": presenter_line,
        "session_suffix": f" (Session {session})" if session else "",
        "session_fa": f" (جلسه‌ی {session.translate(FA_DIGITS)})" if session else "",
        "abstract": " ".join(str(talk.get("abstract", "")).split()),
        "date_long": talk["date"].strftime("%A, %-d %B %Y"),
        "date_short": talk["date"].strftime("%a %-d %b"),
        "date_fa": date_fa(talk["date"]),
        "time_tehran": cfg["time_tehran"],
        "time_utc": cfg["time_utc"],
        "time_fa": cfg["time_tehran"].translate(FA_DIGITS),
        "meet_url": circle["meet_url"],
        "calendar_url": circle["google_calendar_url"],
        "youtube_url": circle["youtube_playlist_url"],
        "talk_url": talk_url(talk, site_url),
        "resources": "\n".join(f"{name}: {url}" for name, url in resources),
        "organizer_name": cfg["organizer_name"],
    }


def render(name, values):
    text = (BOT_DIR / "templates" / f"{name}.txt").read_text(encoding="utf-8")
    return string.Template(text).substitute(values).strip()


def email_parts(name, values):
    """Split a rendered email template into (subject, body)."""
    first, _, body = render(name, values).partition("\n")
    return first.removeprefix("Subject:").strip(), body.strip()


def texts_markdown(kind, talk, cfg, circle, site_url):
    """Markdown with the email and Telegram text for `kind` ("7day" or "1day")."""
    values = template_values(talk, cfg, circle, site_url)
    subject, body = email_parts(f"email-{kind}", values)
    telegram = render(f"telegram-{kind}", values)
    return (f"### Email\n\n**To:** {circle['contact_email']}  \n**Subject:** {subject}\n\n"
            f"```text\n{body}\n```\n\n"
            f"### Telegram (Persian, polish before you post)\n\n```text\n{telegram}\n```\n")


# ---------------------------------------------------------------- GitHub

class GitHub:
    def __init__(self, repo, token, dry_run):
        self.repo = repo
        self.token = token
        self.dry_run = dry_run

    def request(self, method, path, body=None):
        if method != "GET" and self.dry_run:
            print(f"[dry run] {method} {path}\n{json.dumps(body, ensure_ascii=False, indent=2)}\n")
            return {"number": 0}
        req = urllib.request.Request(
            f"https://api.github.com/repos/{self.repo}{path}",
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={"Authorization": f"Bearer {self.token}",
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"})
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
        return json.loads(data) if data else {}

    def bot_issues(self):
        """All issues (open and closed) with the bot label, keyed by marker."""
        if not self.token:
            return {}
        issues, page = {}, 1
        while True:
            batch = self.request(
                "GET", f"/issues?labels={BOT_LABEL}&state=all&per_page=100&page={page}")
            for issue in batch:
                match = re.search(r"<!-- seminar-bot:(\S+) -->", issue.get("body") or "")
                if match:
                    issues[match.group(1)] = issue
            if len(batch) < 100:
                return issues
            page += 1

    def comment_keys(self, number):
        if not self.token or not number:
            return set()
        comments = self.request("GET", f"/issues/{number}/comments?per_page=100")
        return set(re.findall(r"<!-- seminar-bot:(\S+) -->", " ".join(c["body"] for c in comments)))

    def ensure_labels(self):
        for name, color in [(BOT_LABEL, "5319e7"), (NEW_TALK_LABEL, "0e8a16")]:
            try:
                self.request("POST", "/labels", {"name": name, "color": color})
            except urllib.error.HTTPError as e:
                if e.code != 422:  # 422 means the label already exists
                    raise


class Bot:
    def __init__(self, gh, cfg):
        self.gh = gh
        self.cfg = cfg
        self.issues = gh.bot_issues()

    def open_issue(self, key, title, body):
        """Open an issue once. Return True if the issue already existed."""
        if key in self.issues:
            return True
        body += "\n\n" + MARKER.format(key)
        print(f"Open issue: {title}")
        self.issues[key] = self.gh.request("POST", "/issues", {
            "title": title, "body": body,
            "labels": [BOT_LABEL], "assignees": [self.cfg["organizer"]]})
        self.issues[key]["new"] = True
        return False

    def comment_once(self, key, comment_key, body):
        issue = self.issues.get(key)
        if not issue or issue.get("new") or issue.get("state") == "closed":
            return
        if comment_key in self.gh.comment_keys(issue["number"]):
            return
        print(f"Comment on #{issue['number']}: {comment_key}")
        self.gh.request("POST", f"/issues/{issue['number']}/comments", {
            "body": f"@{self.cfg['organizer']} {body}\n\n" + MARKER.format(comment_key)})

    def close(self, key, reason):
        issue = self.issues[key]
        print(f"Close #{issue['number']}: {reason}")
        self.gh.request("POST", f"/issues/{issue['number']}/comments", {"body": reason})
        self.gh.request("PATCH", f"/issues/{issue['number']}", {"state": "closed"})


# ---------------------------------------------------------------- commands

def cmd_run(args):
    cfg, circle, talks = load_config(), load_circle(), load_talks()
    site_url = load_yaml(ROOT / "_config.yml")["url"]
    repo = os.environ.get("GITHUB_REPOSITORY", "learning-theory-circle/learning-theory-circle.github.io")
    gh = GitHub(repo, os.environ.get("GITHUB_TOKEN"), args.dry_run)
    if not args.dry_run:
        gh.ensure_labels()
    bot = Bot(gh, cfg)

    today = args.today or dt.datetime.now(ZoneInfo("Asia/Tehran")).date()
    session = next_session(today, cfg)
    days_left = (session - today).days
    talk = talk_on(talks, session)
    previous = talk_before(talks, session)
    print(f"Today {today}. Next session {session} ({days_left} days). "
          f"Talk: {talk['id'] if talk else 'missing'}.")

    # Close issues whose task the data in talks.yml shows as done.
    by_id = {t["id"]: t for t in talks}
    for key, issue in list(bot.issues.items()):
        if issue.get("state") != "open":
            continue
        kind, _, ref = key.partition(":")
        if kind == "talk-data" and talk_on(talks, dt.date.fromisoformat(ref)):
            bot.close(key, f"The talk for {ref} is now in `_data/talks.yml`. Closing.")
        elif kind == "video" and by_id.get(ref, {}).get("video"):
            bot.close(key, f"The video of `{ref}` is now on the website. Closing.")

    # 1. Ask for the talk data.
    if talk is None and days_left <= cfg["request_days_before"]:
        key = f"talk-data:{session}"
        form = (f"https://github.com/{repo}/issues/new?" + urllib.parse.urlencode(
            {"template": "new-talk.yml", "title": f"New talk: {session}", "date": str(session)}))
        bot.open_issue(key, f"Talk data needed for the session on {session:%a %-d %b}", (
            f"@{cfg['organizer']}, the session on **{session:%A, %-d %B %Y}** has no talk in "
            f"`_data/talks.yml` yet.\n\n"
            f"1. Get the title, abstract, and links from the presenter.\n"
            f"2. Fill in the [New talk form]({form}). The date is already filled in.\n"
            f"3. The bot makes a pull request from the form. Examine it and merge it.\n\n"
            f"The announcement email is due on **{session - dt.timedelta(days=7):%a %-d %b}**. "
            f"This issue closes automatically when the talk is in `_data/talks.yml`."))
        if days_left <= 7:
            bot.comment_once(key, f"{key}:overdue",
                             "The announcement email is now overdue. Please fill in the form today.")
        elif days_left <= 9:
            bot.comment_once(key, f"{key}:urgent",
                             f"The announcement email is due in {days_left - 7} days. "
                             "Please fill in the form soon.")
        elif days_left <= 11:
            bot.comment_once(key, f"{key}:reminder", "Reminder: this talk still has no data.")

    # 2. Announcement email, 7 days before.
    if talk and 1 < days_left <= 7:
        bot.open_issue(f"email-7day:{session}",
                       f"Send the announcement email for {session:%a %-d %b}", (
            f"@{cfg['organizer']}, it is time to announce the next session.\n\n"
            f"1. Send the email below to the Google Group.\n"
            f"2. Polish the Telegram text and post it on the channel.\n"
            f"3. Close this issue.\n\n"
            + texts_markdown("7day", talk, cfg, circle, site_url)))

    # 3. Reminder email, 1 day before.
    if talk and days_left == 1:
        bot.open_issue(f"email-1day:{session}",
                       f"Send the reminder email for tomorrow, {session:%a %-d %b}", (
            f"@{cfg['organizer']}, the session is tomorrow.\n\n"
            f"1. Send the email below to the Google Group.\n"
            f"2. Polish the Telegram text and post it on the channel.\n"
            f"3. Close this issue.\n\n"
            + texts_markdown("1day", talk, cfg, circle, site_url)))

    # 4. Video of the previous session.
    if previous and not previous.get("video") and \
            today >= previous["date"] + dt.timedelta(days=cfg["video_days_after"]):
        key = f"video:{previous['id']}"
        bot.open_issue(key, f"Upload the video of {previous['date']:%a %-d %b}", (
            f"@{cfg['organizer']}, the talk **{previous['title']}** by {previous['presenter']} "
            f"on {previous['date']:%-d %B} has no video on the website.\n\n"
            f"1. Upload the recording to the [YouTube playlist]({circle['youtube_playlist_url']}).\n"
            f"2. Add `video: \"<YouTube link>\"` to the talk `{previous['id']}` in `_data/talks.yml`.\n"
            f"3. If there are slides or notes, add them too.\n\n"
            f"This issue closes automatically when the video link is in `_data/talks.yml`."))
        if days_left <= 3:
            bot.comment_once(key, f"{key}:reminder",
                             f"The next session is in {days_left} days and this video is still missing.")


def cmd_preview(args):
    cfg, circle = load_config(), load_circle()
    site_url = load_yaml(ROOT / "_config.yml")["url"]
    talk = next((t for t in load_talks() if t["id"] == args.talk_id), None)
    if talk is None:
        sys.exit(f"No talk with id {args.talk_id}")
    print("## Announcement (7 days before)\n")
    print(texts_markdown("7day", talk, cfg, circle, site_url))
    print("## Reminder (1 day before)\n")
    print(texts_markdown("1day", talk, cfg, circle, site_url))


def parse_form(body):
    """Read the answers of a GitHub issue form, keyed by field id."""
    labels = {label: key for key, label in FORM_FIELDS}
    answers = {}
    for label, value in re.findall(r"^### (.+?)\s*\n(.*?)(?=^### |\Z)", body, re.M | re.S):
        value = value.strip()
        if label in labels and value and value != "_No response_":
            answers[labels[label]] = value
    return answers


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def yaml_value(key, value):
    if key in ("date", "id"):
        return value
    if key == "abstract":
        value = " ".join(value.split())
    return json.dumps(value, ensure_ascii=False)  # a JSON string is a valid YAML string


def write_talk(talk):
    """Add the entry to talks.yml, or replace the entry with the same id."""
    entry = "\n".join(f"{'- ' if i == 0 else '  '}{key}: {yaml_value(key, talk[key])}"
                      for i, key in enumerate(k for k in TALK_KEYS if talk.get(k))) + "\n"
    lines = TALKS_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith("- ")] + [len(lines)]
    for start, end in zip(starts, starts[1:]):
        if re.search(rf"^\s*id: \"?{re.escape(talk['id'])}\"?\s*$", "".join(lines[start:end]), re.M):
            lines[start:end] = [entry, "\n"]
            break
    else:
        lines[starts[0]:starts[0]] = [entry, "\n"]
    TALKS_FILE.write_text("".join(lines), encoding="utf-8")


def cmd_add_talk(args):
    answers = parse_form(Path(args.issue_body).read_text(encoding="utf-8"))
    missing = [label for key, label in FORM_FIELDS
               if key in ("date", "presenter", "title", "abstract") and key not in answers]
    if missing:
        sys.exit(f"The form has no value for: {', '.join(missing)}")
    date = dt.date.fromisoformat(answers["date"])
    talk = dict(answers, id=f"{slugify(answers['presenter'])}-{date:%Y}-{date:%b}-{date:%d}".lower())
    write_talk(talk)

    page = f"---\nlayout: talk\ntalk_id: {talk['id']}\nnav_exclude: true\n---\n"
    if talk.get("side_notes"):
        page += f"\n## Side Notes\n{talk['side_notes']}\n"
    (PAGES_DIR / f"{talk['id']}.md").write_text(page, encoding="utf-8")

    cfg = load_config()
    if next_session(date, cfg) != date:
        print(f"warning=The date {date} is not on the {cfg['cadence_days']}-day cycle "
              f"that starts on {cfg['anchor_date']}.")
    print(f"id={talk['id']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--today", type=dt.date.fromisoformat, help="pretend today is YYYY-MM-DD")
    run.add_argument("--dry-run", action="store_true", help="print the actions, change nothing")
    run.set_defaults(func=cmd_run)
    preview = sub.add_parser("preview")
    preview.add_argument("talk_id")
    preview.set_defaults(func=cmd_preview)
    add = sub.add_parser("add-talk")
    add.add_argument("issue_body", help="file with the body of a New talk issue")
    add.set_defaults(func=cmd_add_talk)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
