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
  adjust     Adjust the order
  bag        Bag it up - order complete!
  blocked    List tickets that are blocked by dependencies
  related    Link related orders together
  compare    Compare ticket branches
  cycle      Detect circular dependencies
  free       Remove the dependency - order is free to proceed
  list       List tickets with optional filters
  needs      Order needs another item first
  note       Add a note to the order
  open       Open the bodega for business
  order      Place a new order at the counter
  peek       Take a look at order details
  prep       Start prepping the order
  query      Output tickets as JSON for scripting
  ready      List tickets that are ready to work on
  reconcile  Reconcile tickets between branches
  remake     Remake an order
  served     Show recently served orders
  split      Split bundled orders
  status     Get ticket status
  transfer   Transfer tickets from another system
  tree       Display dependency tree
```

## License

MIT
