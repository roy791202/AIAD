"""Pending Gherkin bindings; Rust module tests remain executable evidence.

These stubs intentionally raise NotImplementedError. No BDD runner or binding
framework is introduced by this documentation slice.
"""

def given_bound_project_with_existing_scene_data(context):
    raise NotImplementedError("Bind isolated project and existing scene fixture")

def when_save_scene_using_requested_path(context, requested_path):
    raise NotImplementedError("Invoke existing scene save input facade")

def then_save_fails_before_filesystem_mutation(context):
    raise NotImplementedError("Assert failure and zero filesystem mutations using recording port")

def then_existing_scene_data_unchanged(context):
    raise NotImplementedError("Compare prior and subsequent scene bytes")

def given_bound_project(context):
    raise NotImplementedError("Bind isolated project fixture")

def then_saved_below_bound_project(context):
    raise NotImplementedError("Assert successful relative path and expected file bytes")
