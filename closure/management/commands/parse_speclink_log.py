import json

from django.core.management.base import BaseCommand, CommandError

from closure.services.parser import SpecLinkParseError, build_evidence_report


class Command(BaseCommand):
    help = "Parse SpecLink summary blocks from a simulation log into evidence JSON."

    def add_arguments(self, parser):
        parser.add_argument("log_path")
        parser.add_argument("--project", required=True)
        parser.add_argument("--run-id", required=True)
        parser.add_argument("--output")

    def handle(self, *args, **options):
        try:
            log_text = open(options["log_path"], encoding="utf-8").read()
            report = build_evidence_report(log_text, options["project"], options["run_id"])
        except OSError as exc:
            raise CommandError(str(exc)) from exc
        except SpecLinkParseError as exc:
            raise CommandError(str(exc)) from exc

        rendered = json.dumps(report, indent=2)
        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as handle:
                handle.write(rendered)
                handle.write("\n")
        else:
            self.stdout.write(rendered)

