"""
Utility package for WikiEval Application.

Re-exports all utility functions from submodules for backward compatibility.
"""

# Re-export from mediawiki_helpers
from app.utils.mediawiki_helpers import (
    extract_page_title_from_url,
    build_mediawiki_revisions_api_params,
    get_mediawiki_headers,
    get_latest_revision_author,
    get_article_size_at_timestamp,
    get_article_wikitext,
    get_mediawiki_user_edit_count,
    MEDIAWIKI_API_TIMEOUT,
    _log_warning,
)

# Re-export from article_metrics
from app.utils.article_metrics import (
    get_article_reference_count,
    get_detailed_reference_counts,
    get_article_image_count,
    get_article_infobox_count,
    get_article_incoming_links,
    get_article_outgoing_links,
    fetch_article_metrics,
    _count_footnotes_from_content,
    _extract_article_content_from_revision,
    _fetch_footnotes_count,
)

# Re-export from wiki_editing
from app.utils.wiki_editing import (
    get_csrf_token,
    prepend_template_to_article,
    append_categories_to_article,
)

# Re-export from wiki_templates
from app.utils.wiki_templates import (
    validate_template_link,
    extract_template_name_from_url,
    check_article_has_template,
)

# Re-export from wiki_categories
from app.utils.wiki_categories import (
    extract_category_name_from_url,
    check_article_has_category,
    crawl_category_articles,
)

# Re-export from access_control
from app.utils.access_control import (
    validate_contest_submission_access,
)
