# stone-typescript-generator

**DEPRECATED - There is work happening [upstream](https://github.com/dropbox/stone/pull/14) to add a built-in TypeScript definition generator to Stone.**

[Stone](https://github.com/dropbox/stone) is a language for specifying APIs and
a tool for generating client libraries for those APIs.

This is a generator which produces TypeScript definition files from `.stone` API
specification files, assuming the API conventions used by Dropbox' official SDK
for JavaScript.

It was created to produce a TypeScript definition file for the [Dropbox V2
JavaScript SDK](https://github.com/dropbox/dropbox-sdk-js)

See [the Stone documentation](https://github.com/dropbox/stone) for information
on how to use this generator and [the Dropbox API
spec](https://github.com/dropbox/dropbox-api-spec) for the Dropbox API specs in
Stone format.

## Usage

 1. Install stone following the instructions in the [Stone repository](https://github.com/dropbox/stone).
 2. Run stone with the generator from this repository

```
stone typescript.stoneg.py . path/to/dropbox-api-spec/*.stone -- dropbox.d.ts
```
