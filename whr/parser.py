"""Recursive-descent parser for the complete WHR v1.0 grammar."""

from __future__ import annotations

from typing import Optional

from . import ast_nodes as ast
from .errors import ParseError
from .lexer import tokenize
from .token import Token, TokenKind


MAX_ARGUMENTS = 255


class Parser:
    """Parse a token stream according to the frozen WHR grammar."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0
        self.function_depth = 0
        self.loop_depth = 0

    def parse(self) -> ast.Program:
        declarations: list[ast.Node] = []
        while not self._check_kind(TokenKind.EOF):
            declarations.append(self._declaration())
        return ast.Program(self._peek(), declarations)

    def _declaration(self) -> ast.Node:
        if self._match_lexeme("shape"):
            return self._shape_declaration(self._previous())
        if self._match_lexeme("craft"):
            return self._function_declaration(self._previous())
        if self._match_lexeme("let"):
            return self._variable_declaration(self._previous())
        return self._statement()

    def _shape_declaration(self, keyword: Token) -> ast.ShapeDeclaration:
        name_token = self._consume_kind(TokenKind.IDENTIFIER, "expected shape name")
        self._consume_lexeme("{", "expected '{' after shape name")
        fields: list[str] = []
        field_tokens: dict[str, Token] = {}
        if self._check_lexeme("}"):
            self._error(self._peek(), "shape declaration requires at least one field")
        while not self._check_lexeme("}"):
            field = self._consume_kind(TokenKind.IDENTIFIER, "expected field name")
            if field.lexeme in field_tokens:
                self._error(field, f"duplicate field '{field.lexeme}'")
            field_tokens[field.lexeme] = field
            fields.append(field.lexeme)
            self._consume_lexeme(";", "expected ';' after field declaration")
        self._consume_lexeme("}", "expected '}' after shape declaration")
        return ast.ShapeDeclaration(keyword, name_token.lexeme, fields)

    def _function_declaration(self, keyword: Token) -> ast.FunctionDeclaration:
        name_token = self._consume_kind(TokenKind.IDENTIFIER, "expected function name")
        self._consume_lexeme("(", "expected '(' after function name")
        parameters: list[str] = []
        parameter_tokens: dict[str, Token] = {}
        if not self._check_lexeme(")"):
            while True:
                parameter = self._consume_kind(
                    TokenKind.IDENTIFIER, "expected parameter name"
                )
                if parameter.lexeme in parameter_tokens:
                    self._error(parameter, f"duplicate parameter '{parameter.lexeme}'")
                parameter_tokens[parameter.lexeme] = parameter
                parameters.append(parameter.lexeme)
                self._check_argument_count(len(parameters), parameter)
                if not self._match_lexeme(","):
                    break
        self._consume_lexeme(")", "expected ')' after parameters")

        old_function_depth = self.function_depth
        old_loop_depth = self.loop_depth
        self.function_depth += 1
        # A loop surrounding a nested function must not make break/continue
        # inside that function legal.
        self.loop_depth = 0
        try:
            body = self._block()
        finally:
            self.function_depth = old_function_depth
            self.loop_depth = old_loop_depth
        return ast.FunctionDeclaration(keyword, name_token.lexeme, parameters, body)

    def _variable_declaration(self, keyword: Token) -> ast.VariableDeclaration:
        name = self._consume_kind(TokenKind.IDENTIFIER, "expected variable name")
        self._consume_lexeme("<-", "expected '<-' after variable name")
        initializer = self._expression()
        self._consume_lexeme(";", "expected ';' after variable declaration")
        return ast.VariableDeclaration(keyword, name.lexeme, initializer)

    def _statement(self) -> ast.Node:
        if self._match_lexeme("when"):
            return self._when_statement(self._previous())
        if self._match_lexeme("repeat"):
            return self._repeat_statement(self._previous())
        if self._match_lexeme("give"):
            return self._give_statement(self._previous())
        if self._match_lexeme("break"):
            token = self._previous()
            if self.loop_depth == 0:
                self._error(token, "'break' is only valid inside a loop")
            self._consume_lexeme(";", "expected ';' after 'break'")
            return ast.BreakStatement(token)
        if self._match_lexeme("continue"):
            token = self._previous()
            if self.loop_depth == 0:
                self._error(token, "'continue' is only valid inside a loop")
            self._consume_lexeme(";", "expected ';' after 'continue'")
            return ast.ContinueStatement(token)
        if self._check_lexeme("{"):
            return self._block()

        expression = self._expression()
        self._consume_lexeme(";", "expected ';' after expression")
        return ast.ExpressionStatement(expression.token, expression)

    def _block(self) -> ast.Block:
        opening = self._consume_lexeme("{", "expected '{'")
        declarations: list[ast.Node] = []
        while not self._check_lexeme("}") and not self._check_kind(TokenKind.EOF):
            declarations.append(self._declaration())
        self._consume_lexeme("}", "expected '}' after block")
        return ast.Block(opening, declarations)

    def _when_statement(self, keyword: Token) -> ast.WhenStatement:
        branches = [ast.WhenBranch(self._expression(), self._block())]
        otherwise: Optional[ast.Block] = None
        while self._match_lexeme("otherwise"):
            if self._match_lexeme("when"):
                branches.append(ast.WhenBranch(self._expression(), self._block()))
            else:
                otherwise = self._block()
                break
        return ast.WhenStatement(keyword, branches, otherwise)

    def _repeat_statement(self, keyword: Token) -> ast.RepeatStatement:
        self._consume_lexeme("while", "expected 'while' after 'repeat'")
        condition = self._expression()
        self.loop_depth += 1
        try:
            body = self._block()
        finally:
            self.loop_depth -= 1
        return ast.RepeatStatement(keyword, condition, body)

    def _give_statement(self, keyword: Token) -> ast.GiveStatement:
        if self.function_depth == 0:
            self._error(keyword, "'give' is only valid inside a function")
        if self._check_lexeme(";"):
            value = None
        else:
            value = self._expression()
        self._consume_lexeme(";", "expected ';' after 'give'")
        return ast.GiveStatement(keyword, value)

    def _expression(self) -> ast.Node:
        return self._assignment()

    def _assignment(self) -> ast.Node:
        expression = self._logic_or()
        if self._match_lexeme("<-"):
            operator = self._previous()
            value = self._assignment()
            if not isinstance(
                expression, (ast.Variable, ast.Index, ast.FieldAccess)
            ):
                self._error(operator, "invalid assignment target")
            return ast.Assignment(operator, expression, value)
        return expression

    def _logic_or(self) -> ast.Node:
        expression = self._logic_and()
        while self._match_lexeme("or"):
            operator = self._previous()
            expression = ast.Binary(expression.token, expression, operator, self._logic_and())
        return expression

    def _logic_and(self) -> ast.Node:
        expression = self._equality()
        while self._match_lexeme("and"):
            operator = self._previous()
            expression = ast.Binary(expression.token, expression, operator, self._equality())
        return expression

    def _equality(self) -> ast.Node:
        expression = self._comparison()
        while self._match_lexeme("==", "!="):
            operator = self._previous()
            expression = ast.Binary(expression.token, expression, operator, self._comparison())
        return expression

    def _comparison(self) -> ast.Node:
        expression = self._term()
        while self._match_lexeme("<", "<=", ">", ">="):
            operator = self._previous()
            expression = ast.Binary(expression.token, expression, operator, self._term())
        return expression

    def _term(self) -> ast.Node:
        expression = self._factor()
        while self._match_lexeme("+", "-"):
            operator = self._previous()
            expression = ast.Binary(expression.token, expression, operator, self._factor())
        return expression

    def _factor(self) -> ast.Node:
        expression = self._unary()
        while self._match_lexeme("*", "/", "%"):
            operator = self._previous()
            expression = ast.Binary(expression.token, expression, operator, self._unary())
        return expression

    def _unary(self) -> ast.Node:
        if self._match_lexeme("-", "not"):
            operator = self._previous()
            return ast.Unary(operator, operator, self._unary())
        return self._call()

    def _call(self) -> ast.Node:
        expression = self._primary()
        while True:
            if self._match_lexeme("("):
                arguments = self._arguments_after_opening_paren()
                expression = ast.Call(expression.token, expression, arguments)
            elif self._match_lexeme("["):
                opening = self._previous()
                index = self._expression()
                self._consume_lexeme("]", "expected ']' after index")
                expression = ast.Index(opening, expression, index)
            elif self._match_lexeme("."):
                dot = self._previous()
                name = self._consume_kind(
                    TokenKind.IDENTIFIER, "expected field name after '.'"
                )
                expression = ast.FieldAccess(dot, expression, name.lexeme)
            else:
                break
        return expression

    def _arguments_after_opening_paren(self) -> list[ast.Node]:
        arguments: list[ast.Node] = []
        if not self._check_lexeme(")"):
            while True:
                arguments.append(self._expression())
                self._check_argument_count(len(arguments), arguments[-1].token)
                if not self._match_lexeme(","):
                    break
        self._consume_lexeme(")", "expected ')' after arguments")
        return arguments

    def _primary(self) -> ast.Node:
        if self._match_kind(TokenKind.INTEGER):
            token = self._previous()
            return ast.Literal(token, token.literal)
        if self._match_kind(TokenKind.STRING):
            token = self._previous()
            return ast.Literal(token, token.literal)
        if self._match_lexeme("true"):
            return ast.Literal(self._previous(), True)
        if self._match_lexeme("false"):
            return ast.Literal(self._previous(), False)
        if self._match_lexeme("null"):
            return ast.Literal(self._previous(), None)
        if self._match_lexeme("form"):
            form_token = self._previous()
            name = self._consume_kind(
                TokenKind.IDENTIFIER, "expected shape type name after 'form'"
            )
            return self._shape_initializer(form_token, name)
        if self._match_kind(TokenKind.IDENTIFIER):
            name = self._previous()
            return ast.Variable(name, name.lexeme)
        if self._match_lexeme("["):
            opening = self._previous()
            elements: list[ast.Node] = []
            if not self._check_lexeme("]"):
                while True:
                    elements.append(self._expression())
                    if not self._match_lexeme(","):
                        break
            self._consume_lexeme("]", "expected ']' after array literal")
            return ast.ArrayLiteral(opening, elements)
        if self._match_lexeme("("):
            expression = self._expression()
            self._consume_lexeme(")", "expected ')' after expression")
            return expression
        self._error(self._peek(), "expected expression")
        raise AssertionError("unreachable")

    def _shape_initializer(self, form_token: Token, name: Token) -> ast.ShapeInitializer:
        self._consume_lexeme("{", "expected '{' after shape type name")
        fields: list[ast.FieldInitializer] = []
        field_names: set[str] = set()
        if self._check_lexeme("}"):
            self._error(self._peek(), "shape initializer requires at least one field")
        while True:
            field = self._consume_kind(TokenKind.IDENTIFIER, "expected field name")
            if field.lexeme in field_names:
                self._error(field, f"duplicate field '{field.lexeme}'")
            field_names.add(field.lexeme)
            self._consume_lexeme(":", "expected ':' after field name")
            fields.append(ast.FieldInitializer(field, field.lexeme, self._expression()))
            if not self._match_lexeme(","):
                break
            if self._check_lexeme("}"):
                break
        self._consume_lexeme("}", "expected '}' after shape initializer")
        return ast.ShapeInitializer(form_token, name.lexeme, fields)

    def _check_argument_count(self, count: int, token: Token) -> None:
        if count > MAX_ARGUMENTS:
            self._error(token, "a call or declaration cannot have more than 255 arguments")

    def _match_kind(self, *kinds: str) -> bool:
        if self._peek().kind in kinds:
            self._advance()
            return True
        return False

    def _match_lexeme(self, *lexemes: str) -> bool:
        if self._peek().lexeme in lexemes:
            self._advance()
            return True
        return False

    def _check_kind(self, kind: str) -> bool:
        return self._peek().kind == kind

    def _check_lexeme(self, lexeme: str) -> bool:
        return self._peek().lexeme == lexeme

    def _consume_kind(self, kind: str, message: str) -> Token:
        if self._check_kind(kind):
            return self._advance()
        self._error(self._peek(), message)
        raise AssertionError("unreachable")

    def _consume_lexeme(self, lexeme: str, message: str) -> Token:
        if self._check_lexeme(lexeme):
            return self._advance()
        self._error(self._peek(), message)
        raise AssertionError("unreachable")

    def _advance(self) -> Token:
        if not self._check_kind(TokenKind.EOF):
            self.current += 1
        return self.tokens[self.current - 1]

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _error(self, token: Token, message: str) -> None:
        raise ParseError(message, token.line, token.column)


def parse_source(source: str) -> ast.Program:
    """Lex and parse source text into a WHR AST."""

    return Parser(tokenize(source)).parse()
