# bodega

Git-native issue tracking for developers and AI agents. Inspired by [beads](https://github.com/steveyegge/beads)
and [ticket](https://github.com/wedow/ticket), but combines both the simplicity of a Markdown-based, file-first
ticket management architecture with the flexibility of git tracking in a dedicated branch.

## Installation

Download `bodega` from [GitHub releases](https://github.com/bjia56/bodega/releases/latest). Place it somewhere in your `PATH`.

### Homebrew

The Homebrew tap [`bjia56/tap`](https://github.com/bjia56/homebrew-tap) supports installing the latest `bodega` from GitHub releases on both MacOS and Linux.

```bash
brew tap bjia56/tap
brew install bodega
```

## Usage

```
Usage: bodega [OPTIONS] COMMAND [ARGS]...

  Bodega - Git-native issue tracking for developers and AI agents

Options:
  --version   Show the Bodega version and exit
  -h, --help  Show this message and exit
  --debug     Enable debug output

Commands:
  blocked  List tickets that are blocked by dependencies
  close    Set ticket status to closed
  closed   List recently closed tickets
  create   Create a new ticket
  cycle    Detect circular dependencies
  dep      Add a dependency (BLOCKER blocks ID)
  edit     Edit ticket properties or open in $EDITOR
  gc       Garbage collect (delete) old closed tickets
  howto    Show useful CLI examples for AI agents.
  import   Import tickets from another system
  init     Initialize a new bodega repository
  link     Create a symmetric link between tickets
  list     List tickets with optional filters
  note     Add a timestamped note to a ticket
  push     Push local bodega branch to remote repository
  query    Output tickets as JSON for scripting
  ready    List tickets that are ready to work on
  reopen   Set ticket status back to open
  show     Display ticket details
  start    Set ticket status to in-progress
  status   Get ticket status
  sync     Synchronize tickets between main and bodega branches
  tree     Display dependency tree
  undep    Remove a dependency
  unlink   Remove a link between tickets
```

## License

MIT
