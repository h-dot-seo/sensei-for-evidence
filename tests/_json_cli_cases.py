"""Exact synthetic rejection matrix shared by regression and opt-in measurement."""
COMMANDS = [('evidence_workflow.py',), ('prisma_reports.py',), ('validate_run.py',), ('research_bundle.py', 'create')]
REJECTIONS = ('{"question":"first","question":"second"}', '{"extra":NaN}', 'null', '[]', '{"\\ud800":1,"\\ud800":2}', '{"question":"\\ud800"}')


def arguments(command, source, target):
    args = [*command[1:], str(source)]
    if command[0] == 'research_bundle.py':
        args.append(str(target))
    return args
