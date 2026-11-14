"""Gherkin step-definition stubs; NOT an executed or configured BDD runner.
Executable verification currently lives in Rust pd_report_call::tests.
"""

def given_projector_and_source_fixtures(context):
    raise NotImplementedError("Pending BDD runner integration: validate fixture manifest and Python availability")

def given_empty_and_passing_reports(context):
    raise NotImplementedError("Pending: load fixture.json and snapshot SPEC/EVID bytes")

def when_requested_concurrently_with_default_destinations(context):
    raise NotImplementedError("Pending: invoke the Rust public boundary concurrently without out_dir")

def then_paths_are_distinct(context):
    raise NotImplementedError("Pending: assert independent HTML and Markdown paths")

def then_content_matches_status_and_fingerprint(context):
    raise NotImplementedError("Pending: compare DTO bodies with files, status and fingerprint")

def then_sources_remain_unchanged(context):
    raise NotImplementedError("Pending: compare source byte snapshots and write_back=false")
