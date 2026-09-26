"""Abstract syntax tree nodes for WHR v1.0."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .token import Token


@dataclass
class Node:
    token: Token


@dataclass
class Program(Node):
    declarations: list[Node] = field(default_factory=list)


@dataclass
class ShapeDeclaration(Node):
    name: str
    fields: list[str]


@dataclass
class FunctionDeclaration(Node):
    name: str
    parameters: list[str]
    body: "Block"


@dataclass
class VariableDeclaration(Node):
    name: str
    initializer: Node


@dataclass
class Block(Node):
    declarations: list[Node] = field(default_factory=list)


@dataclass
class WhenBranch:
    condition: Node
    body: Block


@dataclass
class WhenStatement(Node):
    branches: list[WhenBranch]
    otherwise: Optional[Block]


@dataclass
class RepeatStatement(Node):
    condition: Node
    body: Block


@dataclass
class GiveStatement(Node):
    value: Optional[Node]


@dataclass
class BreakStatement(Node):
    pass


@dataclass
class ContinueStatement(Node):
    pass


@dataclass
class ExpressionStatement(Node):
    expression: Node


@dataclass
class Literal(Node):
    value: object


@dataclass
class Variable(Node):
    name: str


@dataclass
class ArrayLiteral(Node):
    elements: list[Node]


@dataclass
class FieldInitializer:
    token: Token
    name: str
    value: Node


@dataclass
class ShapeInitializer(Node):
    name: str
    fields: list[FieldInitializer]


@dataclass
class Unary(Node):
    operator: Token
    operand: Node


@dataclass
class Binary(Node):
    left: Node
    operator: Token
    right: Node


@dataclass
class Assignment(Node):
    target: Node
    value: Node


@dataclass
class Call(Node):
    callee: Node
    arguments: list[Node]


@dataclass
class Index(Node):
    object: Node
    index: Node


@dataclass
class FieldAccess(Node):
    object: Node
    name: str
