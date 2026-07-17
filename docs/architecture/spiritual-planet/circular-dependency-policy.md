# Circular dependency policy

## Rule

Cross-module state changes must terminate at a user decision or a source-module
fact. No module may automatically turn its own downstream outcome into a new
upstream command.

Correct loop:

```text
Twin context -> recommendation proposal -> arbitration -> user confirmation
-> target-module command -> target-module fact -> versioned metadata event
-> later Twin observation -> user review
```

Incorrect loop:

```text
Twin pattern -> automatic habit -> missed habit -> automatic negative pattern
-> more automatic habits
```

Safeguards are a maximum of 20 candidates, 20 workflow nodes and three model
calls at contract level; production defaults are eight nodes and one model
call. Batch 9's deterministic workflow uses zero model calls. Every ordinary
command expires, is idempotent and requires a user-confirmation reference.
