#!/usr/bin/env python3

from __future__ import unicode_literals

from argparse import ArgumentParser

from stone.generator import CodeGenerator
from stone import data_type

_cmdline_parser = ArgumentParser(prog='ts-def-generator')
_cmdline_parser.add_argument(
    'filename',
    help=('The name of the generated .d.ts file containing all routes and structs'),
)


_header = """\
// Auto-generated by typescript.stoneg.py, do not modify.
"""


_primitive_type_map = {
    'Bytes': 'string',
    'Boolean': 'boolean',
    'Float32': 'number',
    'Float64': 'number',
    'Int32': 'number',
    # Although JavaScript cannot represent the full range of 64bit ints in its
    # `number` type, it appears that Dropbox does use a number when serializing
    # such types to JSON.
    'Int64': 'number',
    'UInt32': 'number',
    'UInt64': 'number',
    'List': 'Array',
    'String': 'string',
    'Timestamp': 'string',
    'Void': 'void',
    }


def format_type(typ):
    """Format a Stone data type as a TypeScript type"""

    # TODO - Where the type is an alias, emit the alias name and then emit
    # `type $alias = $wrapped;`
    """Return a TypeScript representation of a stone DataType"""
    if data_type.is_nullable_type(typ):
        wrapped_type, _ = data_type.unwrap_nullable(typ)

        # If the type is nullable, assume that it has been marked as an
        # optional member of the containing struct, ie. "field?: type", so we
        # don't need to represent the fact that it might be null in the
        # formatted type. ie. There is no need to generate "field?: type |
        # null"
        return '{}'.format(format_type(wrapped_type))

    if data_type.is_primitive_type(typ):
        return _primitive_type_map.get(typ.name)
    elif data_type.is_list_type(typ):
        return '{}[]'.format(format_type(typ.data_type))
    else:
        return typ.name


def camelcase(str):
    """
    Convert a string separated by underscores or slashes to camelCase.

    eg: alpha/get_metadata => alphaGetMetadata
    """
    idx = str.find('_')
    if idx == -1:
        idx = str.find('/')
    if idx == -1:
        return str
    else:
        converted_name = str[0:idx] + str[idx+1].upper() + str[idx+2:]
        return camelcase(converted_name)


def route_method_name(namespace, route):
    return camelcase(namespace + '_' + route)


class TypeScriptDefinitionGenerator(CodeGenerator):
    """Generates a TypeScript definition file for a JavaScript stone client."""

    cmdline_parser = _cmdline_parser

    def generate(self, api):
        # TODO - Make these configurable
        cls_name = 'Dropbox'
        mod_name = 'dropbox'

        with self.output_to_relative_path(self.args.filename):

            # Generate interface definitions for user-defined types
            for namespace in api.namespaces.values():
                for typ in namespace.linearize_data_types():
                    if data_type.is_struct_type(typ):
                        self._generate_interface(typ)
                    elif data_type.is_union_type(typ):
                        self._generate_union_interface(typ)
                
            # Generate route definition
            with self.block('declare module "{}"'.format(mod_name)):
                with self.block('class {}'.format(cls_name)):
                    for namespace in api.namespaces.values():
                        for route in namespace.routes:
                            self._generate_method(namespace, route)

                self.emit('export = {};'.format(cls_name))

    def _generate_union_interface(self, typ):
        """Generate a TypeScript `interface {}` for a Stone union type"""

        if typ.doc:
            self._emit_docstring(typ.doc)

        # This currently emits an interface where each union variant is
        # expressed as an optional field.  We might be able to get better type
        # safety by using TypeScript's support for discriminated unions
        # instead.
        #
        # See https://github.com/Microsoft/TypeScript/pull/9163
        extends_clause = ''
        if typ.parent_type:
            # Stone union extensions are not compatible with TypeScript,
            # so just add a comment for documentation purposes
            extends_clause = ' /* extends {} */'.format(typ.parent_type.name)

        with self.block('interface {}{}'.format(typ.name, extends_clause)):
            variant_names = [f.name for f in typ.all_fields if f != typ.catch_all_field]
            tags = ["'{}'".format(name) for name in variant_names]

            if typ.catch_all_field:
                tags.append('string')

            self.emit("'.tag': {}".format(' | '.join(tags)))

            for field in typ.all_fields:
                if field.doc:
                    self._emit_docstring(field.doc)

                # Emit type declaration. Union variants may have void type, in
                # which case we still emit a '$name: void' declaration because
                # this is valid TypeScript and it provides somewhere to put a
                # docstring
                self.emit('{}?: {};'.format(field.name, format_type(field.data_type)))


    def _generate_interface(self, typ):
        """Generate a TypeScript `interface {}` for a Stone struct"""

        if typ.doc:
            self._emit_docstring(typ.doc)

        extends_clause = ''
        if typ.parent_type:
            extends_clause = ' extends {}'.format(typ.parent_type.name)

        with self.block('interface {}{}'.format(typ.name, extends_clause)):
            if typ.has_enumerated_subtypes():
                tag_types = ["'{}'".format(t.name) for t in typ.get_enumerated_subtypes()]
                self.emit("'.tag': {}".format(' | '.join(tag_types)))

            for field in typ.all_fields:
                if field.doc:
                    self._emit_docstring(field.doc)
                is_required = field in typ.all_required_fields
                self.emit('{}{}: {};'.format(field.name,
                    '?' if not is_required else '',
                    format_type(field.data_type)))
    
    def _generate_method(self, namespace, route):
        """Generate a method declaration for a Stone route"""

        if route.doc:
            self._emit_docstring(route.doc)

        method_name = route_method_name(namespace.name, route.name)
        if data_type.is_void_type(route.arg_data_type):
            arg_str = ''
        else:
            arg_str = 'arg: {}'.format(format_type(route.arg_data_type))

        # Methods in Stone are parameterized by (arg type, return type, error
        # type) The TypeScript `Promise` type however is only parameterized by
        # one type, so although we generate interface definitions for the error
        # types, they are not used to parameterize the result here.
        self.emit('{}({}): Promise<{}>;'.format(method_name,
            arg_str,
            format_type(route.result_data_type)))

    def _emit_docstring(self, str):
        str = str.replace('\n',' ')

        if len(str) < 70:
            self.emit('/** {} */'.format(str))
        else:
            self.emit('/**')
            self.emit_wrapped_text(str, prefix=' * ')
            self.emit(' */')
