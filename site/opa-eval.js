/**
 * Minimal OPA WASM ABI 1.2 loader for Enact.
 *
 * Evaluates a module produced by `opa build -t wasm` (OPA 1.8.x, Rego v1).
 * Implements the sprintf host builtin used by the library policies.
 * Does not implement I/O builtins (http.send, etc.).
 *
 * ABI: https://www.openpolicyagent.org/docs/latest/wasm/
 * Not a copy of @open-policy-agent/opa-wasm; vendored here so Pages never
 * fetches a CDN.
 */
(function (root) {
  "use strict";

  var encoder = new TextEncoder();
  var decoder = new TextDecoder();

  function cstr(memory, addr) {
    var bytes = new Uint8Array(memory.buffer, addr);
    var end = 0;
    while (bytes[end] !== 0) {
      end += 1;
    }
    return decoder.decode(bytes.subarray(0, end));
  }

  function sprintf(fmt, values) {
    var i = 0;
    var list = Array.isArray(values) ? values : [];
    return String(fmt).replace(/%(?:%|[-+#0 ]*\d*(?:\.\d+)?[vTtdfsgbxX])/g, function (token) {
      if (token === "%%") {
        return "%";
      }
      var value = list[i];
      i += 1;
      var spec = token.charAt(token.length - 1);
      if (spec === "s") {
        return String(value);
      }
      if (spec === "d") {
        return String(Math.trunc(Number(value)));
      }
      if (typeof value === "string") {
        return value;
      }
      return JSON.stringify(value);
    });
  }

  function loadPolicy(wasmBytes) {
    var memory = new WebAssembly.Memory({ initial: 32 });
    var exports = null;
    var builtinById = {};

    function dump(addr) {
      return JSON.parse(cstr(memory, exports.opa_json_dump(addr)));
    }

    function loadJson(value) {
      var encoded = encoder.encode(JSON.stringify(value));
      var rawAddr = exports.opa_malloc(encoded.length);
      new Uint8Array(memory.buffer, rawAddr, encoded.length).set(encoded);
      var parsed = exports.opa_json_parse(rawAddr, encoded.length);
      if (!parsed) {
        throw new Error("OPA wasm could not parse a host builtin result");
      }
      return parsed;
    }

    function callBuiltin(id, args) {
      var name = builtinById[id];
      if (name === "sprintf") {
        return loadJson(sprintf(args[0], args[1]));
      }
      throw new Error("OPA host builtin not implemented: " + (name || id));
    }

    var imports = {
      env: {
        memory: memory,
        opa_abort: function (addr) {
          throw new Error(cstr(memory, addr));
        },
        opa_println: function (addr) {
          if (typeof console !== "undefined") {
            console.log(cstr(memory, addr));
          }
        },
        opa_builtin0: function (id) {
          return callBuiltin(id, []);
        },
        opa_builtin1: function (id, _ctx, a) {
          return callBuiltin(id, [dump(a)]);
        },
        opa_builtin2: function (id, _ctx, a, b) {
          return callBuiltin(id, [dump(a), dump(b)]);
        },
        opa_builtin3: function (id, _ctx, a, b, c) {
          return callBuiltin(id, [dump(a), dump(b), dump(c)]);
        },
        opa_builtin4: function (id, _ctx, a, b, c, d) {
          return callBuiltin(id, [dump(a), dump(b), dump(c), dump(d)]);
        },
      },
    };

    return WebAssembly.instantiate(wasmBytes, imports).then(function (result) {
      exports = result.instance.exports;
      var builtins = dump(exports.builtins());
      Object.keys(builtins).forEach(function (name) {
        builtinById[builtins[name]] = name;
      });
      var entrypoints = dump(exports.entrypoints());
      return {
        abi: exports.opa_wasm_abi_version.value,
        abiMinor: exports.opa_wasm_abi_minor_version.value,
        builtins: builtins,
        entrypoints: entrypoints,
        evaluate: function (input, entrypoint) {
          var entryId = 0;
          if (typeof entrypoint === "number") {
            entryId = entrypoint;
          } else if (typeof entrypoint === "string") {
            if (!(entrypoint in entrypoints)) {
              throw new Error("unknown wasm entrypoint: " + entrypoint);
            }
            entryId = entrypoints[entrypoint];
          }
          var encoded = encoder.encode(JSON.stringify(input));
          var inputAddr = exports.opa_malloc(encoded.length);
          new Uint8Array(memory.buffer, inputAddr, encoded.length).set(encoded);
          var heapPtr = exports.opa_heap_ptr_get();
          var resultAddr = exports.opa_eval(0, entryId, 0, inputAddr, encoded.length, heapPtr, 0);
          return JSON.parse(cstr(memory, resultAddr));
        },
      };
    });
  }

  function interpretResult(raw) {
    if (!Array.isArray(raw) || !raw.length || !raw[0] || raw[0].result === undefined) {
      throw new Error("OPA wasm returned no result");
    }
    var value = raw[0].result;
    if (typeof value === "boolean") {
      return { passed: value, message: "Policy returned a boolean result." };
    }
    if (value && typeof value === "object") {
      var passed;
      if ("passed" in value) {
        passed = Boolean(value.passed);
      } else if ("allow" in value) {
        passed = Boolean(value.allow);
      } else {
        throw new Error("result object must include passed or allow");
      }
      var message = value.message || (passed ? "Check passed." : "Check failed.");
      return { passed: passed, message: String(message), raw: value };
    }
    throw new Error("unexpected result type");
  }

  var api = { loadPolicy: loadPolicy, interpretResult: interpretResult };

  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EnactOpa = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
