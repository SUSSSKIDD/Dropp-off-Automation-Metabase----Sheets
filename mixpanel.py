import os
import requests
from datetime import date

MIXPANEL_API_SECRET = os.environ["MIXPANEL_API_SECRET"]

_JQL_TEMPLATE = """\
function main() {
  return Events({
    from_date: '2026-01-01',
    to_date: '%(to_date)s'
  })
  .filter(function(e) {
    return String(e.properties.pre_user_id) === '%(pre_user_id)s'
    && e.properties.pageName === 'teaser_page_viewed'
    && e.properties.source === 'profiling_agent_lp_airo'
  })
  .map(function(e) {
    return {
      pre_user_id: e.properties.pre_user_id,
      pageUrl: e.properties.pageUrl
    }
  })
}
"""


def fetch_airo_link(pre_user_id: str) -> str:
    script = _JQL_TEMPLATE % {
        "to_date": date.today().isoformat(),
        "pre_user_id": pre_user_id.replace("'", "\\'"),
    }
    try:
        resp = requests.post(
            "https://mixpanel.com/api/2.0/jql",
            auth=(MIXPANEL_API_SECRET, ""),
            data={"script": script},
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json()
        if results and isinstance(results, list) and results[0].get("pageUrl"):
            return results[0]["pageUrl"]
        return "NOT FOUND"
    except Exception:
        return "API ERROR"
