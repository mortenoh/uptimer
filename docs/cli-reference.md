# CLI Reference

## Global Options

### `--version`

Show version and exit.

```bash
uptimer --version
```

### `--json`

Output as JSON instead of rich console output.

```bash
uptimer --json check example.com
```

## Commands

### `check`

Check if a URL is up.

```bash
uptimer check [OPTIONS] URL
```

**Arguments:**

- `URL` - The URL to check (required)

**Options:**

- `-c`, `--checker` - Checker to use (default: `http`)
- `-v`, `--verbose` - Show detailed request info

**Examples:**

```bash
# Basic check
uptimer check google.com

# With verbose output
uptimer check google.com -v

# Use specific checker
uptimer check google.com -c http
```

### `checkers`

List available checkers.

```bash
uptimer checkers
```

**Output:**

```
  http - HTTP check with redirect following
```

### `version`

Show version information.

```bash
uptimer version
```
