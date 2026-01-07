# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/mixins/output_handler.py
# module: quack_core.tools.mixins.output_handler
# role: module
# neighbors: __init__.py, env_init.py, integration_enabled.py, lifecycle.py
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===


"""
DEPRECATED: OutputFormatMixin has been removed.

Output handling is now the exclusive responsibility of runners (Ring C).
Tools (Ring B) return CapabilityResult with typed data, and runners
decide how to persist that data.

Migration:
- Remove OutputFormatMixin from tool inheritance
- Remove _get_output_extension() override
- Remove get_output_writer() override
- Return data in CapabilityResult, let runner handle persistence

Old pattern (DEPRECATED):
    class MyTool(OutputFormatMixin, BaseQuackTool):
        def _get_output_extension(self):
            return ".yaml"

New pattern (Doctrine-compliant):
    class MyTool(BaseQuackTool):
        def run(self, request, ctx):
            result = {"key": "value"}
            return CapabilityResult.ok(
                data=result,
                msg="Processing completed"
            )

    # Runner decides output format based on configuration
"""

# This file intentionally left empty to document the removal
# Do not add any code here - output handling is runner responsibility
