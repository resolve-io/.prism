#!/usr/bin/env python3
"""Tests for tree-sitter entity and relationship extraction in brain_engine.py."""

import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from brain_engine import (
    Brain,
    _get_treesitter_parser,
    _TS_LANG_MAP,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parser_for(suffix: str):
    lang = _TS_LANG_MAP.get(suffix)
    return _get_treesitter_parser(lang) if lang else None


def _extract(filepath: str, content: str):
    """Run tree-sitter extraction and return (entities, relationships)."""
    suffix = Path(filepath).suffix.lower()
    parser = _parser_for(suffix)
    if parser is None:
        pytest.skip(f"tree-sitter parser not available for {suffix}")
    return Brain._extract_entities_treesitter(filepath, content, parser, suffix)


# ---------------------------------------------------------------------------
# Python extraction
# ---------------------------------------------------------------------------

class TestPythonExtraction:
    SAMPLE = """\
import os
from pathlib import Path

class Foo(Bar):
    def method(self):
        baz()

def top_func():
    Foo()
"""

    def test_entities_classes(self):
        entities, _ = _extract("sample.py", self.SAMPLE)
        names = {(n, k) for n, k, _ in entities}
        assert ("Foo", "class") in names

    def test_entities_functions(self):
        entities, _ = _extract("sample.py", self.SAMPLE)
        names = {(n, k) for n, k, _ in entities}
        assert ("method", "function") in names
        assert ("top_func", "function") in names

    def test_entities_file_module(self):
        entities, _ = _extract("sample.py", self.SAMPLE)
        names = {(n, k) for n, k, _ in entities}
        assert ("sample", "file") in names

    def test_relationship_imports(self):
        _, rels = _extract("sample.py", self.SAMPLE)
        rel_set = {(s, t, r) for s, t, r in rels}
        assert ("sample", "os", "imports") in rel_set
        assert ("sample", "pathlib", "imports") in rel_set

    def test_relationship_extends(self):
        _, rels = _extract("sample.py", self.SAMPLE)
        rel_set = {(s, t, r) for s, t, r in rels}
        assert ("Foo", "Bar", "extends") in rel_set

    def test_relationship_calls(self):
        _, rels = _extract("sample.py", self.SAMPLE)
        rel_set = {(s, t, r) for s, t, r in rels}
        assert ("method", "baz", "calls") in rel_set

    def test_line_numbers(self):
        entities, _ = _extract("sample.py", self.SAMPLE)
        foo_entry = next((e for e in entities if e[0] == "Foo"), None)
        assert foo_entry is not None
        assert foo_entry[2] == 4  # class Foo is on line 4

    def test_no_entities_empty_file(self):
        entities, rels = _extract("empty.py", "")
        # Only file entity
        assert all(k == "file" for _, k, _ in entities)
        assert rels == []

    def test_async_function(self):
        code = "async def async_func():\n    pass\n"
        entities, _ = _extract("afile.py", code)
        names = {n for n, k, _ in entities if k == "function"}
        assert "async_func" in names


# ---------------------------------------------------------------------------
# TypeScript extraction
# ---------------------------------------------------------------------------

class TestTypeScriptExtraction:
    SAMPLE = """\
import { Foo } from './foo';
import path from 'path';

class Bar extends Baz {
  method(): void {
    doSomething();
  }
}

export function myFunc() {
  const x = new Bar();
}
"""

    def test_entities_classes(self):
        entities, _ = _extract("app.ts", self.SAMPLE)
        names = {(n, k) for n, k, _ in entities}
        assert ("Bar", "class") in names

    def test_entities_methods(self):
        entities, _ = _extract("app.ts", self.SAMPLE)
        names = {(n, k) for n, k, _ in entities}
        assert ("method", "method") in names

    def test_entities_exported_function(self):
        entities, _ = _extract("app.ts", self.SAMPLE)
        names = {(n, k) for n, k, _ in entities}
        assert ("myFunc", "function") in names

    def test_relationship_imports(self):
        _, rels = _extract("app.ts", self.SAMPLE)
        rel_set = {(s, t, r) for s, t, r in rels}
        assert ("app", "foo", "imports") in rel_set
        assert ("app", "path", "imports") in rel_set

    def test_relationship_extends(self):
        _, rels = _extract("app.ts", self.SAMPLE)
        rel_set = {(s, t, r) for s, t, r in rels}
        assert ("Bar", "Baz", "extends") in rel_set

    def test_relationship_calls(self):
        _, rels = _extract("app.ts", self.SAMPLE)
        rel_set = {(s, t, r) for s, t, r in rels}
        assert ("method", "doSomething", "calls") in rel_set

    def test_file_entity(self):
        entities, _ = _extract("app.ts", self.SAMPLE)
        names = {(n, k) for n, k, _ in entities}
        assert ("app", "file") in names


# ---------------------------------------------------------------------------
# JavaScript extraction
# ---------------------------------------------------------------------------

class TestJavaScriptExtraction:
    SAMPLE = """\
import React from 'react';

class MyComponent extends React.Component {
  render() {
    return null;
  }
}

export function helper() {
  doWork();
}
"""

    def test_entities_class(self):
        entities, _ = _extract("comp.js", self.SAMPLE)
        names = {n for n, k, _ in entities if k == "class"}
        assert "MyComponent" in names

    def test_relationship_imports(self):
        _, rels = _extract("comp.js", self.SAMPLE)
        mods = {t for s, t, r in rels if r == "imports"}
        assert "react" in mods

    def test_relationship_calls(self):
        _, rels = _extract("comp.js", self.SAMPLE)
        rel_set = {(s, t, r) for s, t, r in rels}
        assert ("helper", "doWork", "calls") in rel_set


# ---------------------------------------------------------------------------
# C# extraction
# ---------------------------------------------------------------------------

class TestCSharpExtraction:
    SAMPLE = """\
using System;
using System.IO;

namespace MyApp {
    class Foo : Bar {
        public void Method() {
            DoSomething();
        }
    }
}
"""

    def test_entities_class(self):
        entities, _ = _extract("Program.cs", self.SAMPLE)
        names = {(n, k) for n, k, _ in entities}
        assert ("Foo", "class") in names

    def test_entities_method(self):
        entities, _ = _extract("Program.cs", self.SAMPLE)
        names = {(n, k) for n, k, _ in entities}
        assert ("Method", "method") in names

    def test_relationship_imports(self):
        _, rels = _extract("Program.cs", self.SAMPLE)
        mods = {t for s, t, r in rels if r == "imports"}
        assert "System" in mods
        assert "System.IO" in mods

    def test_relationship_extends(self):
        _, rels = _extract("Program.cs", self.SAMPLE)
        rel_set = {(s, t, r) for s, t, r in rels}
        assert ("Foo", "Bar", "extends") in rel_set

    def test_relationship_calls(self):
        _, rels = _extract("Program.cs", self.SAMPLE)
        rel_set = {(s, t, r) for s, t, r in rels}
        assert ("Method", "DoSomething", "calls") in rel_set


# ---------------------------------------------------------------------------
# Fallback: regex extraction when tree-sitter unavailable
# ---------------------------------------------------------------------------

class TestRegexFallback:
    def test_regex_extracts_python_class(self):
        content = "class Foo:\n    pass\n"
        entities = Brain._extract_entities("test.py", content)
        names = {(n, k) for n, k, _ in entities}
        assert ("Foo", "class") in names

    def test_regex_extracts_python_function(self):
        content = "def bar():\n    pass\n"
        entities = Brain._extract_entities("test.py", content)
        names = {(n, k) for n, k, _ in entities}
        assert ("bar", "function") in names

    def test_regex_extracts_js_class(self):
        content = "export class MyClass {}\n"
        entities = Brain._extract_entities("test.js", content)
        names = {(n, k) for n, k, _ in entities}
        assert ("MyClass", "class") in names

    def test_regex_always_adds_file_entity(self):
        entities = Brain._extract_entities("mymodule.py", "x = 1\n")
        names = {(n, k) for n, k, _ in entities}
        assert ("mymodule", "file") in names


# ---------------------------------------------------------------------------
# Integration: _index_graph writes relationships to graph DB
# ---------------------------------------------------------------------------

class TestIndexGraphIntegration:
    def test_relationships_stored_in_db(self, tmp_path):
        brain_dir = tmp_path / ".prism" / "brain"
        brain_dir.mkdir(parents=True, exist_ok=True)
        b = Brain(
            brain_db=str(brain_dir / "brain.db"),
            graph_db=str(brain_dir / "graph.db"),
            scores_db=str(brain_dir / "scores.db"),
        )
        content = """\
import os

class Parent:
    pass

class Child(Parent):
    def do_thing(self):
        helper()
"""
        b._index_graph("module.py", content)
        rows = b._graph.execute("SELECT COUNT(*) FROM relationships").fetchone()
        assert rows[0] > 0

    def test_extends_relationship_stored(self, tmp_path):
        brain_dir = tmp_path / ".prism" / "brain"
        brain_dir.mkdir(parents=True, exist_ok=True)
        b = Brain(
            brain_db=str(brain_dir / "brain.db"),
            graph_db=str(brain_dir / "graph.db"),
            scores_db=str(brain_dir / "scores.db"),
        )
        content = "class Child(Parent):\n    pass\n"
        b._index_graph("mod.py", content)
        rows = b._graph.execute(
            "SELECT r.relation FROM relationships r "
            "JOIN entities s ON r.source_id = s.id "
            "JOIN entities t ON r.target_id = t.id "
            "WHERE s.name = 'Child' AND t.name = 'Parent'"
        ).fetchall()
        relations = [r["relation"] for r in rows]
        assert "extends" in relations
