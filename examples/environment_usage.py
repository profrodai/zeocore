"""Run without credentials: inspect distinct managed test and production state."""

from pathlib import Path
from tempfile import TemporaryDirectory

from zeo_core.integrations.environments import IntegrationEnvironment


def main() -> None:
    with TemporaryDirectory(prefix="zeocore-environments-") as temporary:
        root = Path(temporary)
        states = []
        for mode in ("test", "production"):
            environment = IntegrationEnvironment(mode, root, ("kit.marketing",))
            environment.prepare()
            child = environment.child_environment({"KIT_API_KEY": "ambient-sentinel"})
            assert "KIT_API_KEY" not in child
            assert (environment.state_dir / "config/integrations.yaml").is_file()
            states.append(environment.state_dir)
            print(f"{mode}: private state prepared; ambient key excluded")
        assert states[0] != states[1]
        print("LOCAL: no provider request; temporary state removed on exit")


if __name__ == "__main__":
    main()
