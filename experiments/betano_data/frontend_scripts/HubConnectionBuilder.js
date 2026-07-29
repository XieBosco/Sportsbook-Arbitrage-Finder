var M = (function() {
    var o = Object.setPrototypeOf || {
        __proto__: []
    }instanceof Array && function(t, e) {
        t.__proto__ = e
    }
    || function(t, e) {
        for (var r in e)
            e.hasOwnProperty(r) && (t[r] = e[r])
    }
    ;
    return function(t, e) {
        o(t, e);
        function r() {
            this.constructor = t
        }
        t.prototype = e === null ? Object.create(e) : (r.prototype = e.prototype,
        new r)
    }
}
)(), O = (function(o) {
    M(t, o);
    function t(e, r) {
        var i = this.constructor
          , n = this
          , c = i.prototype;
        return n = o.call(this, e) || this,
        n.statusCode = r,
        n.__proto__ = c,
        n
    }
    return t
}
)(Error), L = (function(o) {
    M(t, o);
    function t(e) {
        var r = this.constructor;
        e === void 0 && (e = "A timeout occurred.");
        var i = this
          , n = r.prototype;
        return i = o.call(this, e) || this,
        i.__proto__ = n,
        i
    }
    return t
}
)(Error), H = (function(o) {
    M(t, o);
    function t(e) {
        var r = this.constructor;
        e === void 0 && (e = "An abort occurred.");
        var i = this
          , n = r.prototype;
        return i = o.call(this, e) || this,
        i.__proto__ = n,
        i
    }
    return t
}
)(Error), U = Object.assign || function(o) {
    for (var t, e = 1, r = arguments.length; e < r; e++) {
        t = arguments[e];
        for (var i in t)
            Object.prototype.hasOwnProperty.call(t, i) && (o[i] = t[i])
    }
    return o
}
, Y = (function() {
    function o(t, e, r) {
        this.statusCode = t,
        this.statusText = e,
        this.content = r
    }
    return o
}
)(), B = (function() {
    function o() {}
    return o.prototype.get = function(t, e) {
        return this.send(U({}, e, {
            method: "GET",
            url: t
        }))
    }
    ,
    o.prototype.post = function(t, e) {
        return this.send(U({}, e, {
            method: "POST",
            url: t
        }))
    }
    ,
    o.prototype.delete = function(t, e) {
        return this.send(U({}, e, {
            method: "DELETE",
            url: t
        }))
    }
    ,
    o.prototype.getCookieString = function(t) {
        return ""
    }
    ,
    o
}
)(), l;
(function(o) {
    o[o.Trace = 0] = "Trace",
    o[o.Debug = 1] = "Debug",
    o[o.Information = 2] = "Information",
    o[o.Warning = 3] = "Warning",
    o[o.Error = 4] = "Error",
    o[o.Critical = 5] = "Critical",
    o[o.None = 6] = "None"
}
)(l || (l = {}));
var $ = (function() {
    function o() {}
    return o.prototype.log = function(t, e) {}
    ,
    o.instance = new o,
    o
}
)()
  , q = Object.assign || function(o) {
    for (var t, e = 1, r = arguments.length; e < r; e++) {
        t = arguments[e];
        for (var i in t)
            Object.prototype.hasOwnProperty.call(t, i) && (o[i] = t[i])
    }
    return o
}
  , ee = function(o, t, e, r) {
    return new (e || (e = Promise))(function(i, n) {
        function c(s) {
            try {
                u(r.next(s))
            } catch (h) {
                n(h)
            }
        }
        function a(s) {
            try {
                u(r.throw(s))
            } catch (h) {
                n(h)
            }
        }
        function u(s) {
            s.done ? i(s.value) : new e(function(h) {
                h(s.value)
            }
            ).then(c, a)
        }
        u((r = r.apply(o, t || [])).next())
    }
    )
}
  , te = function(o, t) {
    var e = {
        label: 0,
        sent: function() {
            if (n[0] & 1)
                throw n[1];
            return n[1]
        },
        trys: [],
        ops: []
    }, r, i, n, c;
    return c = {
        next: a(0),
        throw: a(1),
        return: a(2)
    },
    typeof Symbol == "function" && (c[Symbol.iterator] = function() {
        return this
    }
    ),
    c;
    function a(s) {
        return function(h) {
            return u([s, h])
        }
    }
    function u(s) {
        if (r)
            throw new TypeError("Generator is already executing.");
        for (; e; )
            try {
                if (r = 1,
                i && (n = s[0] & 2 ? i.return : s[0] ? i.throw || ((n = i.return) && n.call(i),
                0) : i.next) && !(n = n.call(i, s[1])).done)
                    return n;
                switch (i = 0,
                n && (s = [s[0] & 2, n.value]),
                s[0]) {
                case 0:
                case 1:
                    n = s;
                    break;
                case 4:
                    return e.label++,
                    {
                        value: s[1],
                        done: !1
                    };
                case 5:
                    e.label++,
                    i = s[1],
                    s = [0];
                    continue;
                case 7:
                    s = e.ops.pop(),
                    e.trys.pop();
                    continue;
                default:
                    if (n = e.trys,
                    !(n = n.length > 0 && n[n.length - 1]) && (s[0] === 6 || s[0] === 2)) {
                        e = 0;
                        continue
                    }
                    if (s[0] === 3 && (!n || s[1] > n[0] && s[1] < n[3])) {
                        e.label = s[1];
                        break
                    }
                    if (s[0] === 6 && e.label < n[1]) {
                        e.label = n[1],
                        n = s;
                        break
                    }
                    if (n && e.label < n[2]) {
                        e.label = n[2],
                        e.ops.push(s);
                        break
                    }
                    n[2] && e.ops.pop(),
                    e.trys.pop();
                    continue
                }
                s = t.call(o, e)
            } catch (h) {
                s = [6, h],
                i = 0
            } finally {
                r = n = 0
            }
        if (s[0] & 5)
            throw s[1];
        return {
            value: s[0] ? s[1] : void 0,
            done: !0
        }
    }
}
  , ne = "5.0.11"
  , w = (function() {
    function o() {}
    return o.isRequired = function(t, e) {
        if (t == null)
            throw new Error("The '" + e + "' argument is required.")
    }
    ,
    o.isNotEmpty = function(t, e) {
        if (!t || t.match(/^\s*$/))
            throw new Error("The '" + e + "' argument should not be empty.")
    }
    ,
    o.isIn = function(t, e, r) {
        if (!(t in e))
            throw new Error("Unknown " + r + " value: " + t + ".")
    }
    ,
    o
}
)()
  , C = (function() {
    function o() {}
    return Object.defineProperty(o, "isBrowser", {
        get: function() {
            return typeof window == "object"
        },
        enumerable: !0,
        configurable: !0
    }),
    Object.defineProperty(o, "isWebWorker", {
        get: function() {
            return typeof self == "object" && "importScripts"in self
        },
        enumerable: !0,
        configurable: !0
    }),
    Object.defineProperty(o, "isNode", {
        get: function() {
            return !this.isBrowser && !this.isWebWorker
        },
        enumerable: !0,
        configurable: !0
    }),
    o
}
)();
function j(o, t) {
    var e = "";
    return F(o) ? (e = "Binary data of length " + o.byteLength,
    t && (e += ". Content: '" + re(o) + "'")) : typeof o == "string" && (e = "String data of length " + o.length,
    t && (e += ". Content: '" + o + "'")),
    e
}
function re(o) {
    var t = new Uint8Array(o)
      , e = "";
    return t.forEach(function(r) {
        var i = r < 16 ? "0" : "";
        e += "0x" + i + r.toString(16) + " "
    }),
    e.substr(0, e.length - 1)
}
function F(o) {
    return o && typeof ArrayBuffer < "u" && (o instanceof ArrayBuffer || o.constructor && o.constructor.name === "ArrayBuffer")
}
function Z(o, t, e, r, i, n, c, a, u) {
    return ee(this, void 0, void 0, function() {
        var s, h, f, d, y, k, v, p;
        return te(this, function(A) {
            switch (A.label) {
            case 0:
                return h = {},
                i ? [4, i()] : [3, 2];
            case 1:
                f = A.sent(),
                f && (h = (s = {},
                s.Authorization = "Bearer " + f,
                s)),
                A.label = 2;
            case 2:
                return d = I(),
                y = d[0],
                k = d[1],
                h[y] = k,
                o.log(l.Trace, "(" + t + " transport) sending data. " + j(n, c) + "."),
                v = F(n) ? "arraybuffer" : "text",
                [4, e.post(r, {
                    content: n,
                    headers: q({}, h, u),
                    responseType: v,
                    withCredentials: a
                })];
            case 3:
                return p = A.sent(),
                o.log(l.Trace, "(" + t + " transport) request complete. Response status: " + p.statusCode + "."),
                [2]
            }
        })
    })
}
function oe(o) {
    return o === void 0 ? new N(l.Information) : o === null ? $.instance : o.log ? o : new N(o)
}
var ie = (function() {
    function o(t, e) {
        this.subject = t,
        this.observer = e
    }
    return o.prototype.dispose = function() {
        var t = this.subject.observers.indexOf(this.observer);
        t > -1 && this.subject.observers.splice(t, 1),
        this.subject.observers.length === 0 && this.subject.cancelCallback && this.subject.cancelCallback().catch(function(e) {})
    }
    ,
    o
}
)()
  , N = (function() {
    function o(t) {
        this.minimumLogLevel = t,
        this.outputConsole = console
    }
    return o.prototype.log = function(t, e) {
        if (t >= this.minimumLogLevel)
            switch (t) {
            case l.Critical:
            case l.Error:
                this.outputConsole.error("[" + new Date().toISOString() + "] " + l[t] + ": " + e);
                break;
            case l.Warning:
                this.outputConsole.warn("[" + new Date().toISOString() + "] " + l[t] + ": " + e);
                break;
            case l.Information:
                this.outputConsole.info("[" + new Date().toISOString() + "] " + l[t] + ": " + e);
                break;
            default:
                this.outputConsole.log("[" + new Date().toISOString() + "] " + l[t] + ": " + e);
                break
            }
    }
    ,
    o
}
)();
function I() {
    var o = "X-SignalR-User-Agent";
    return C.isNode && (o = "User-Agent"),
    [o, se(ne, ce(), ue(), ae())]
}
function se(o, t, e, r) {
    var i = "Microsoft SignalR/"
      , n = o.split(".");
    return i += n[0] + "." + n[1],
    i += " (" + o + "; ",
    t && t !== "" ? i += t + "; " : i += "Unknown OS; ",
    i += "" + e,
    r ? i += "; " + r : i += "; Unknown Runtime Version",
    i += ")",
    i
}
function ce() {
    if (C.isNode)
        switch (process.platform) {
        case "win32":
            return "Windows NT";
        case "darwin":
            return "macOS";
        case "linux":
            return "Linux";
        default:
            return process.platform
        }
    else
        return ""
}
function ae() {
    if (C.isNode)
        return process.versions.node
}
function ue() {
    return C.isNode ? "NodeJS" : "Browser"
}
var le = (function() {
    var o = Object.setPrototypeOf || {
        __proto__: []
    }instanceof Array && function(t, e) {
        t.__proto__ = e
    }
    || function(t, e) {
        for (var r in e)
            e.hasOwnProperty(r) && (t[r] = e[r])
    }
    ;
    return function(t, e) {
        o(t, e);
        function r() {
            this.constructor = t
        }
        t.prototype = e === null ? Object.create(e) : (r.prototype = e.prototype,
        new r)
    }
}
)()
  , he = Object.assign || function(o) {
    for (var t, e = 1, r = arguments.length; e < r; e++) {
        t = arguments[e];
        for (var i in t)
            Object.prototype.hasOwnProperty.call(t, i) && (o[i] = t[i])
    }
    return o
}
  , fe = function(o, t, e, r) {
    return new (e || (e = Promise))(function(i, n) {
        function c(s) {
            try {
                u(r.next(s))
            } catch (h) {
                n(h)
            }
        }
        function a(s) {
            try {
                u(r.throw(s))
            } catch (h) {
                n(h)
            }
        }
        function u(s) {
            s.done ? i(s.value) : new e(function(h) {
                h(s.value)
            }
            ).then(c, a)
        }
        u((r = r.apply(o, t || [])).next())
    }
    )
}
  , de = function(o, t) {
    var e = {
        label: 0,
        sent: function() {
            if (n[0] & 1)
                throw n[1];
            return n[1]
        },
        trys: [],
        ops: []
    }, r, i, n, c;
    return c = {
        next: a(0),
        throw: a(1),
        return: a(2)
    },
    typeof Symbol == "function" && (c[Symbol.iterator] = function() {
        return this
    }
    ),
    c;
    function a(s) {
        return function(h) {
            return u([s, h])
        }
    }
    function u(s) {
        if (r)
            throw new TypeError("Generator is already executing.");
        for (; e; )
            try {
                if (r = 1,
                i && (n = s[0] & 2 ? i.return : s[0] ? i.throw || ((n = i.return) && n.call(i),
                0) : i.next) && !(n = n.call(i, s[1])).done)
                    return n;
                switch (i = 0,
                n && (s = [s[0] & 2, n.value]),
                s[0]) {
                case 0:
                case 1:
                    n = s;
                    break;
                case 4:
                    return e.label++,
                    {
                        value: s[1],
                        done: !1
                    };
                case 5:
                    e.label++,
                    i = s[1],
                    s = [0];
                    continue;
                case 7:
                    s = e.ops.pop(),
                    e.trys.pop();
                    continue;
                default:
                    if (n = e.trys,
                    !(n = n.length > 0 && n[n.length - 1]) && (s[0] === 6 || s[0] === 2)) {
                        e = 0;
                        continue
                    }
                    if (s[0] === 3 && (!n || s[1] > n[0] && s[1] < n[3])) {
                        e.label = s[1];
                        break
                    }
                    if (s[0] === 6 && e.label < n[1]) {
                        e.label = n[1],
                        n = s;
                        break
                    }
                    if (n && e.label < n[2]) {
                        e.label = n[2],
                        e.ops.push(s);
                        break
                    }
                    n[2] && e.ops.pop(),
                    e.trys.pop();
                    continue
                }
                s = t.call(o, e)
            } catch (h) {
                s = [6, h],
                i = 0
            } finally {
                r = n = 0
            }
        if (s[0] & 5)
            throw s[1];
        return {
            value: s[0] ? s[1] : void 0,
            done: !0
        }
    }
}
  , pe = (function(o) {
    le(t, o);
    function t(e) {
        var r = o.call(this) || this;
        if (r.logger = e,
        typeof fetch > "u") {
            var i = typeof __webpack_require__ == "function" ? __non_webpack_require__ : require;
            r.jar = new (i("tough-cookie")).CookieJar,
            r.fetchType = i("node-fetch"),
            r.fetchType = i("fetch-cookie")(r.fetchType, r.jar),
            r.abortControllerType = i("abort-controller")
        } else
            r.fetchType = fetch.bind(self),
            r.abortControllerType = AbortController;
        return r
    }
    return t.prototype.send = function(e) {
        return fe(this, void 0, void 0, function() {
            var r, i, n, c, a, u, s, h, f = this;
            return de(this, function(d) {
                switch (d.label) {
                case 0:
                    if (e.abortSignal && e.abortSignal.aborted)
                        throw new H;
                    if (!e.method)
                        throw new Error("No method defined.");
                    if (!e.url)
                        throw new Error("No url defined.");
                    r = new this.abortControllerType,
                    e.abortSignal && (e.abortSignal.onabort = function() {
                        r.abort(),
                        i = new H
                    }
                    ),
                    n = null,
                    e.timeout && (c = e.timeout,
                    n = setTimeout(function() {
                        r.abort(),
                        f.logger.log(l.Warning, "Timeout from HTTP request."),
                        i = new L
                    }, c)),
                    d.label = 1;
                case 1:
                    return d.trys.push([1, 3, 4, 5]),
                    [4, this.fetchType(e.url, {
                        body: e.content,
                        cache: "no-cache",
                        credentials: e.withCredentials === !0 ? "include" : "same-origin",
                        headers: he({
                            "Content-Type": "text/plain;charset=UTF-8",
                            "X-Requested-With": "XMLHttpRequest"
                        }, e.headers),
                        method: e.method,
                        mode: "cors",
                        redirect: "manual",
                        signal: r.signal
                    })];
                case 2:
                    return a = d.sent(),
                    [3, 5];
                case 3:
                    throw u = d.sent(),
                    i || (this.logger.log(l.Warning, "Error from HTTP request. " + u + "."),
                    u);
                case 4:
                    return n && clearTimeout(n),
                    e.abortSignal && (e.abortSignal.onabort = null),
                    [7];
                case 5:
                    if (!a.ok)
                        throw new O(a.statusText,a.status);
                    return s = ge(a, e.responseType),
                    [4, s];
                case 6:
                    return h = d.sent(),
                    [2, new Y(a.status,a.statusText,h)]
                }
            })
        })
    }
    ,
    t.prototype.getCookieString = function(e) {
        var r = "";
        return C.isNode && this.jar && this.jar.getCookies(e, function(i, n) {
            return r = n.join("; ")
        }),
        r
    }
    ,
    t
}
)(B);
function ge(o, t) {
    var e;
    switch (t) {
    case "arraybuffer":
        e = o.arrayBuffer();
        break;
    case "text":
        e = o.text();
        break;
    case "blob":
    case "document":
    case "json":
        throw new Error(t + " is not supported.");
    default:
        e = o.text();
        break
    }
    return e
}
var ve = (function() {
    var o = Object.setPrototypeOf || {
        __proto__: []
    }instanceof Array && function(t, e) {
        t.__proto__ = e
    }
    || function(t, e) {
        for (var r in e)
            e.hasOwnProperty(r) && (t[r] = e[r])
    }
    ;
    return function(t, e) {
        o(t, e);
        function r() {
            this.constructor = t
        }
        t.prototype = e === null ? Object.create(e) : (r.prototype = e.prototype,
        new r)
    }
}
)(), be = (function(o) {
    ve(t, o);
    function t(e) {
        var r = o.call(this) || this;
        return r.logger = e,
        r
    }
    return t.prototype.send = function(e) {
        var r = this;
        return e.abortSignal && e.abortSignal.aborted ? Promise.reject(new H) : e.method ? e.url ? new Promise(function(i, n) {
            var c = new XMLHttpRequest;
            c.open(e.method, e.url, !0),
            c.withCredentials = e.withCredentials === void 0 ? !0 : e.withCredentials,
            c.setRequestHeader("X-Requested-With", "XMLHttpRequest"),
            c.setRequestHeader("Content-Type", "text/plain;charset=UTF-8");
            var a = e.headers;
            a && Object.keys(a).forEach(function(u) {
                c.setRequestHeader(u, a[u])
            }),
            e.responseType && (c.responseType = e.responseType),
            e.abortSignal && (e.abortSignal.onabort = function() {
                c.abort(),
                n(new H)
            }
            ),
            e.timeout && (c.timeout = e.timeout),
            c.onload = function() {
                e.abortSignal && (e.abortSignal.onabort = null),
                c.status >= 200 && c.status < 300 ? i(new Y(c.status,c.statusText,c.response || c.responseText)) : n(new O(c.statusText,c.status))
            }
            ,
            c.onerror = function() {
                r.logger.log(l.Warning, "Error from HTTP request. " + c.status + ": " + c.statusText + "."),
                n(new O(c.statusText,c.status))
            }
            ,
            c.ontimeout = function() {
                r.logger.log(l.Warning, "Timeout from HTTP request."),
                n(new L)
            }
            ,
            c.send(e.content || "")
        }
        ) : Promise.reject(new Error("No url defined.")) : Promise.reject(new Error("No method defined."))
    }
    ,
    t
}
)(B), ye = (function() {
    var o = Object.setPrototypeOf || {
        __proto__: []
    }instanceof Array && function(t, e) {
        t.__proto__ = e
    }
    || function(t, e) {
        for (var r in e)
            e.hasOwnProperty(r) && (t[r] = e[r])
    }
    ;
    return function(t, e) {
        o(t, e);
        function r() {
            this.constructor = t
        }
        t.prototype = e === null ? Object.create(e) : (r.prototype = e.prototype,
        new r)
    }
}
)(), we = (function(o) {
    ye(t, o);
    function t(e) {
        var r = o.call(this) || this;
        if (typeof fetch < "u" || C.isNode)
            r.httpClient = new pe(e);
        else if (typeof XMLHttpRequest < "u")
            r.httpClient = new be(e);
        else
            throw new Error("No usable HttpClient found.");
        return r
    }
    return t.prototype.send = function(e) {
        return e.abortSignal && e.abortSignal.aborted ? Promise.reject(new H) : e.method ? e.url ? this.httpClient.send(e) : Promise.reject(new Error("No url defined.")) : Promise.reject(new Error("No method defined."))
    }
    ,
    t.prototype.getCookieString = function(e) {
        return this.httpClient.getCookieString(e)
    }
    ,
    t
}
)(B), T = (function() {
    function o() {}
    return o.write = function(t) {
        return "" + t + o.RecordSeparator
    }
    ,
    o.parse = function(t) {
        if (t[t.length - 1] !== o.RecordSeparator)
            throw new Error("Message is incomplete.");
        var e = t.split(o.RecordSeparator);
        return e.pop(),
        e
    }
    ,
    o.RecordSeparatorCode = 30,
    o.RecordSeparator = String.fromCharCode(o.RecordSeparatorCode),
    o
}
)(), me = (function() {
    function o() {}
    return o.prototype.writeHandshakeRequest = function(t) {
        return T.write(JSON.stringify(t))
    }
    ,
    o.prototype.parseHandshakeResponse = function(t) {
        var e, r, i;
        if (F(t) || typeof Buffer < "u" && t instanceof Buffer) {
            var n = new Uint8Array(t)
              , c = n.indexOf(T.RecordSeparatorCode);
            if (c === -1)
                throw new Error("Message is incomplete.");
            var a = c + 1;
            r = String.fromCharCode.apply(null, n.slice(0, a)),
            i = n.byteLength > a ? n.slice(a).buffer : null
        } else {
            var u = t
              , c = u.indexOf(T.RecordSeparator);
            if (c === -1)
                throw new Error("Message is incomplete.");
            var a = c + 1;
            r = u.substring(0, a),
            i = u.length > a ? u.substring(a) : null
        }
        var s = T.parse(r)
          , h = JSON.parse(s[0]);
        if (h.type)
            throw new Error("Expected a handshake response from the server.");
        return e = h,
        [i, e]
    }
    ,
    o
}
)(), g;
(function(o) {
    o[o.Invocation = 1] = "Invocation",
    o[o.StreamItem = 2] = "StreamItem",
    o[o.Completion = 3] = "Completion",
    o[o.StreamInvocation = 4] = "StreamInvocation",
    o[o.CancelInvocation = 5] = "CancelInvocation",
    o[o.Ping = 6] = "Ping",
    o[o.Close = 7] = "Close"
}
)(g || (g = {}));
var Se = (function() {
    function o() {
        this.observers = []
    }
    return o.prototype.next = function(t) {
        for (var e = 0, r = this.observers; e < r.length; e++) {
            var i = r[e];
            i.next(t)
        }
    }
    ,
    o.prototype.error = function(t) {
        for (var e = 0, r = this.observers; e < r.length; e++) {
            var i = r[e];
            i.error && i.error(t)
        }
    }
    ,
    o.prototype.complete = function() {
        for (var t = 0, e = this.observers; t < e.length; t++) {
            var r = e[t];
            r.complete && r.complete()
        }
    }
    ,
    o.prototype.subscribe = function(t) {
        return this.observers.push(t),
        new ie(this,t)
    }
    ,
    o
}
)(), _ = function(o, t, e, r) {
    return new (e || (e = Promise))(function(i, n) {
        function c(s) {
            try {
                u(r.next(s))
            } catch (h) {
                n(h)
            }
        }
        function a(s) {
            try {
                u(r.throw(s))
            } catch (h) {
                n(h)
            }
        }
        function u(s) {
            s.done ? i(s.value) : new e(function(h) {
                h(s.value)
            }
            ).then(c, a)
        }
        u((r = r.apply(o, t || [])).next())
    }
    )
}, D = function(o, t) {
    var e = {
        label: 0,
        sent: function() {
            if (n[0] & 1)
                throw n[1];
            return n[1]
        },
        trys: [],
        ops: []
    }, r, i, n, c;
    return c = {
        next: a(0),
        throw: a(1),
        return: a(2)
    },
    typeof Symbol == "function" && (c[Symbol.iterator] = function() {
        return this
    }
    ),
    c;
    function a(s) {
        return function(h) {
            return u([s, h])
        }
    }
    function u(s) {
        if (r)
            throw new TypeError("Generator is already executing.");
        for (; e; )
            try {
                if (r = 1,
                i && (n = s[0] & 2 ? i.return : s[0] ? i.throw || ((n = i.return) && n.call(i),
                0) : i.next) && !(n = n.call(i, s[1])).done)
                    return n;
                switch (i = 0,
                n && (s = [s[0] & 2, n.value]),
                s[0]) {
                case 0:
                case 1:
                    n = s;
                    break;
                case 4:
                    return e.label++,
                    {
                        value: s[1],
                        done: !1
                    };
                case 5:
                    e.label++,
                    i = s[1],
                    s = [0];
                    continue;
                case 7:
                    s = e.ops.pop(),
                    e.trys.pop();
                    continue;
                default:
                    if (n = e.trys,
                    !(n = n.length > 0 && n[n.length - 1]) && (s[0] === 6 || s[0] === 2)) {
                        e = 0;
                        continue
                    }
                    if (s[0] === 3 && (!n || s[1] > n[0] && s[1] < n[3])) {
                        e.label = s[1];
                        break
                    }
                    if (s[0] === 6 && e.label < n[1]) {
                        e.label = n[1],
                        n = s;
                        break
                    }
                    if (n && e.label < n[2]) {
                        e.label = n[2],
                        e.ops.push(s);
                        break
                    }
                    n[2] && e.ops.pop(),
                    e.trys.pop();
                    continue
                }
                s = t.call(o, e)
            } catch (h) {
                s = [6, h],
                i = 0
            } finally {
                r = n = 0
            }
        if (s[0] & 5)
            throw s[1];
        return {
            value: s[0] ? s[1] : void 0,
            done: !0
        }
    }
}, Ce = 30 * 1e3, ke = 15 * 1e3, b;
(function(o) {
    o.Disconnected = "Disconnected",
    o.Connecting = "Connecting",
    o.Connected = "Connected",
    o.Disconnecting = "Disconnecting",
    o.Reconnecting = "Reconnecting"
}
)(b || (b = {}));
var Ee = (function() {
    function o(t, e, r, i) {
        var n = this;
        this.nextKeepAlive = 0,
        w.isRequired(t, "connection"),
        w.isRequired(e, "logger"),
        w.isRequired(r, "protocol"),
        this.serverTimeoutInMilliseconds = Ce,
        this.keepAliveIntervalInMilliseconds = ke,
        this.logger = e,
        this.protocol = r,
        this.connection = t,
        this.reconnectPolicy = i,
        this.handshakeProtocol = new me,
        this.connection.onreceive = function(c) {
            return n.processIncomingData(c)
        }
        ,
        this.connection.onclose = function(c) {
            return n.connectionClosed(c)
        }
        ,
        this.callbacks = {},
        this.methods = {},
        this.closedCallbacks = [],
        this.reconnectingCallbacks = [],
        this.reconnectedCallbacks = [],
        this.invocationId = 0,
        this.receivedHandshakeResponse = !1,
        this.connectionState = b.Disconnected,
        this.connectionStarted = !1,
        this.cachedPingMessage = this.protocol.writeMessage({
            type: g.Ping
        })
    }
    return o.create = function(t, e, r, i) {
        return new o(t,e,r,i)
    }
    ,
    Object.defineProperty(o.prototype, "state", {
        get: function() {
            return this.connectionState
        },
        enumerable: !0,
        configurable: !0
    }),
    Object.defineProperty(o.prototype, "connectionId", {
        get: function() {
            return this.connection && this.connection.connectionId || null
        },
        enumerable: !0,
        configurable: !0
    }),
    Object.defineProperty(o.prototype, "baseUrl", {
        get: function() {
            return this.connection.baseUrl || ""
        },
        set: function(t) {
            if (this.connectionState !== b.Disconnected && this.connectionState !== b.Reconnecting)
                throw new Error("The HubConnection must be in the Disconnected or Reconnecting state to change the url.");
            if (!t)
                throw new Error("The HubConnection url must be a valid url.");
            this.connection.baseUrl = t
        },
        enumerable: !0,
        configurable: !0
    }),
    o.prototype.start = function() {
        return this.startPromise = this.startWithStateTransitions(),
        this.startPromise
    }
    ,
    o.prototype.startWithStateTransitions = function() {
        return _(this, void 0, void 0, function() {
            var t;
            return D(this, function(e) {
                switch (e.label) {
                case 0:
                    if (this.connectionState !== b.Disconnected)
                        return [2, Promise.reject(new Error("Cannot start a HubConnection that is not in the 'Disconnected' state."))];
                    this.connectionState = b.Connecting,
                    this.logger.log(l.Debug, "Starting HubConnection."),
                    e.label = 1;
                case 1:
                    return e.trys.push([1, 3, , 4]),
                    [4, this.startInternal()];
                case 2:
                    return e.sent(),
                    this.connectionState = b.Connected,
                    this.connectionStarted = !0,
                    this.logger.log(l.Debug, "HubConnection connected successfully."),
                    [3, 4];
                case 3:
                    return t = e.sent(),
                    this.connectionState = b.Disconnected,
                    this.logger.log(l.Debug, "HubConnection failed to start successfully because of error '" + t + "'."),
                    [2, Promise.reject(t)];
                case 4:
                    return [2]
                }
            })
        })
    }
    ,
    o.prototype.startInternal = function() {
        return _(this, void 0, void 0, function() {
            var t, e, r, i = this;
            return D(this, function(n) {
                switch (n.label) {
                case 0:
                    return this.stopDuringStartError = void 0,
                    this.receivedHandshakeResponse = !1,
                    t = new Promise(function(c, a) {
                        i.handshakeResolver = c,
                        i.handshakeRejecter = a
                    }
                    ),
                    [4, this.connection.start(this.protocol.transferFormat)];
                case 1:
                    n.sent(),
                    n.label = 2;
                case 2:
                    return n.trys.push([2, 5, , 7]),
                    e = {
                        protocol: this.protocol.name,
                        version: this.protocol.version
                    },
                    this.logger.log(l.Debug, "Sending handshake request."),
                    [4, this.sendMessage(this.handshakeProtocol.writeHandshakeRequest(e))];
                case 3:
                    return n.sent(),
                    this.logger.log(l.Information, "Using HubProtocol '" + this.protocol.name + "'."),
                    this.cleanupTimeout(),
                    this.resetTimeoutPeriod(),
                    this.resetKeepAliveInterval(),
                    [4, t];
                case 4:
                    if (n.sent(),
                    this.stopDuringStartError)
                        throw this.stopDuringStartError;
                    return [3, 7];
                case 5:
                    return r = n.sent(),
                    this.logger.log(l.Debug, "Hub handshake failed with error '" + r + "' during start(). Stopping HubConnection."),
                    this.cleanupTimeout(),
                    this.cleanupPingTimer(),
                    [4, this.connection.stop(r)];
                case 6:
                    throw n.sent(),
                    r;
                case 7:
                    return [2]
                }
            })
        })
    }
    ,
    o.prototype.stop = function() {
        return _(this, void 0, void 0, function() {
            var t;
            return D(this, function(e) {
                switch (e.label) {
                case 0:
                    return t = this.startPromise,
                    this.stopPromise = this.stopInternal(),
                    [4, this.stopPromise];
                case 1:
                    e.sent(),
                    e.label = 2;
                case 2:
                    return e.trys.push([2, 4, , 5]),
                    [4, t];
                case 3:
                    return e.sent(),
                    [3, 5];
                case 4:
                    return e.sent(),
                    [3, 5];
                case 5:
                    return [2]
                }
            })
        })
    }
    ,
    o.prototype.stopInternal = function(t) {
        return this.connectionState === b.Disconnected ? (this.logger.log(l.Debug, "Call to HubConnection.stop(" + t + ") ignored because it is already in the disconnected state."),
        Promise.resolve()) : this.connectionState === b.Disconnecting ? (this.logger.log(l.Debug, "Call to HttpConnection.stop(" + t + ") ignored because the connection is already in the disconnecting state."),
        this.stopPromise) : (this.connectionState = b.Disconnecting,
        this.logger.log(l.Debug, "Stopping HubConnection."),
        this.reconnectDelayHandle ? (this.logger.log(l.Debug, "Connection stopped during reconnect delay. Done reconnecting."),
        clearTimeout(this.reconnectDelayHandle),
        this.reconnectDelayHandle = void 0,
        this.completeClose(),
        Promise.resolve()) : (this.cleanupTimeout(),
        this.cleanupPingTimer(),
        this.stopDuringStartError = t || new Error("The connection was stopped before the hub handshake could complete."),
        this.connection.stop(t)))
    }
    ,
    o.prototype.stream = function(t) {
        for (var e = this, r = [], i = 1; i < arguments.length; i++)
            r[i - 1] = arguments[i];
        var n = this.replaceStreamingParams(r), c = n[0], a = n[1], u = this.createStreamInvocation(t, r, a), s, h = new Se;
        return h.cancelCallback = function() {
            var f = e.createCancelInvocation(u.invocationId);
            return delete e.callbacks[u.invocationId],
            s.then(function() {
                return e.sendWithProtocol(f)
            })
        }
        ,
        this.callbacks[u.invocationId] = function(f, d) {
            if (d) {
                h.error(d);
                return
            } else
                f && (f.type === g.Completion ? f.error ? h.error(new Error(f.error)) : h.complete() : h.next(f.item))
        }
        ,
        s = this.sendWithProtocol(u).catch(function(f) {
            h.error(f),
            delete e.callbacks[u.invocationId]
        }),
        this.launchStreams(c, s),
        h
    }
    ,
    o.prototype.sendMessage = function(t) {
        return this.resetKeepAliveInterval(),
        this.connection.send(t)
    }
    ,
    o.prototype.sendWithProtocol = function(t) {
        return this.sendMessage(this.protocol.writeMessage(t))
    }
    ,
    o.prototype.send = function(t) {
        for (var e = [], r = 1; r < arguments.length; r++)
            e[r - 1] = arguments[r];
        var i = this.replaceStreamingParams(e)
          , n = i[0]
          , c = i[1]
          , a = this.sendWithProtocol(this.createInvocation(t, e, !0, c));
        return this.launchStreams(n, a),
        a
    }
    ,
    o.prototype.invoke = function(t) {
        for (var e = this, r = [], i = 1; i < arguments.length; i++)
            r[i - 1] = arguments[i];
        var n = this.replaceStreamingParams(r)
          , c = n[0]
          , a = n[1]
          , u = this.createInvocation(t, r, !1, a)
          , s = new Promise(function(h, f) {
            e.callbacks[u.invocationId] = function(y, k) {
                if (k) {
                    f(k);
                    return
                } else
                    y && (y.type === g.Completion ? y.error ? f(new Error(y.error)) : h(y.result) : f(new Error("Unexpected message type: " + y.type)))
            }
            ;
            var d = e.sendWithProtocol(u).catch(function(y) {
                f(y),
                delete e.callbacks[u.invocationId]
            });
            e.launchStreams(c, d)
        }
        );
        return s
    }
    ,
    o.prototype.on = function(t, e) {
        !t || !e || (t = t.toLowerCase(),
        this.methods[t] || (this.methods[t] = []),
        this.methods[t].indexOf(e) === -1 && this.methods[t].push(e))
    }
    ,
    o.prototype.off = function(t, e) {
        if (t) {
            t = t.toLowerCase();
            var r = this.methods[t];
            if (r)
                if (e) {
                    var i = r.indexOf(e);
                    i !== -1 && (r.splice(i, 1),
                    r.length === 0 && delete this.methods[t])
                } else
                    delete this.methods[t]
        }
    }
    ,
    o.prototype.onclose = function(t) {
        t && this.closedCallbacks.push(t)
    }
    ,
    o.prototype.onreconnecting = function(t) {
        t && this.reconnectingCallbacks.push(t)
    }
    ,
    o.prototype.onreconnected = function(t) {
        t && this.reconnectedCallbacks.push(t)
    }
    ,
    o.prototype.processIncomingData = function(t) {
        if (this.cleanupTimeout(),
        this.receivedHandshakeResponse || (t = this.processHandshakeResponse(t),
        this.receivedHandshakeResponse = !0),
        t)
            for (var e = this.protocol.parseMessages(t, this.logger), r = 0, i = e; r < i.length; r++) {
                var n = i[r];
                switch (n.type) {
                case g.Invocation:
                    this.invokeClientMethod(n);
                    break;
                case g.StreamItem:
                case g.Completion:
                    var c = this.callbacks[n.invocationId];
                    c && (n.type === g.Completion && delete this.callbacks[n.invocationId],
                    c(n));
                    break;
                case g.Ping:
                    break;
                case g.Close:
                    this.logger.log(l.Information, "Close message received from server.");
                    var a = n.error ? new Error("Server returned an error on close: " + n.error) : void 0;
                    n.allowReconnect === !0 ? this.connection.stop(a) : this.stopPromise = this.stopInternal(a);
                    break;
                default:
                    this.logger.log(l.Warning, "Invalid message type: " + n.type + ".");
                    break
                }
            }
        this.resetTimeoutPeriod()
    }
    ,
    o.prototype.processHandshakeResponse = function(t) {
        var e, r, i;
        try {
            e = this.handshakeProtocol.parseHandshakeResponse(t),
            i = e[0],
            r = e[1]
        } catch (a) {
            var n = "Error parsing handshake response: " + a;
            this.logger.log(l.Error, n);
            var c = new Error(n);
            throw this.handshakeRejecter(c),
            c
        }
        if (r.error) {
            var n = "Server returned handshake error: " + r.error;
            this.logger.log(l.Error, n);
            var c = new Error(n);
            throw this.handshakeRejecter(c),
            c
        } else
            this.logger.log(l.Debug, "Server handshake complete.");
        return this.handshakeResolver(),
        i
    }
    ,
    o.prototype.resetKeepAliveInterval = function() {
        this.connection.features.inherentKeepAlive || (this.nextKeepAlive = new Date().getTime() + this.keepAliveIntervalInMilliseconds,
        this.cleanupPingTimer())
    }
    ,
    o.prototype.resetTimeoutPeriod = function() {
        var t = this;
        if ((!this.connection.features || !this.connection.features.inherentKeepAlive) && (this.timeoutHandle = setTimeout(function() {
            return t.serverTimeout()
        }, this.serverTimeoutInMilliseconds),
        this.pingServerHandle === void 0)) {
            var e = this.nextKeepAlive - new Date().getTime();
            e < 0 && (e = 0),
            this.pingServerHandle = setTimeout(function() {
                return _(t, void 0, void 0, function() {
                    return D(this, function(r) {
                        switch (r.label) {
                        case 0:
                            if (this.connectionState !== b.Connected)
                                return [3, 4];
                            r.label = 1;
                        case 1:
                            return r.trys.push([1, 3, , 4]),
                            [4, this.sendMessage(this.cachedPingMessage)];
                        case 2:
                            return r.sent(),
                            [3, 4];
                        case 3:
                            return r.sent(),
                            this.cleanupPingTimer(),
                            [3, 4];
                        case 4:
                            return [2]
                        }
                    })
                })
            }, e)
        }
    }
    ,
    o.prototype.serverTimeout = function() {
        this.connection.stop(new Error("Server timeout elapsed without receiving a message from the server."))
    }
    ,
    o.prototype.invokeClientMethod = function(t) {
        var e = this
          , r = this.methods[t.target.toLowerCase()];
        if (r) {
            try {
                r.forEach(function(n) {
                    return n.apply(e, t.arguments)
                })
            } catch (n) {
                this.logger.log(l.Error, "A callback for the method " + t.target.toLowerCase() + " threw error '" + n + "'.")
            }
            if (t.invocationId) {
                var i = "Server requested a response, which is not supported in this version of the client.";
                this.logger.log(l.Error, i),
                this.stopPromise = this.stopInternal(new Error(i))
            }
        } else
            this.logger.log(l.Warning, "No client method with the name '" + t.target + "' found.")
    }
    ,
    o.prototype.connectionClosed = function(t) {
        this.logger.log(l.Debug, "HubConnection.connectionClosed(" + t + ") called while in state " + this.connectionState + "."),
        this.stopDuringStartError = this.stopDuringStartError || t || new Error("The underlying connection was closed before the hub handshake could complete."),
        this.handshakeResolver && this.handshakeResolver(),
        this.cancelCallbacksWithError(t || new Error("Invocation canceled due to the underlying connection being closed.")),
        this.cleanupTimeout(),
        this.cleanupPingTimer(),
        this.connectionState === b.Disconnecting ? this.completeClose(t) : this.connectionState === b.Connected && this.reconnectPolicy ? this.reconnect(t) : this.connectionState === b.Connected && this.completeClose(t)
    }
    ,
    o.prototype.completeClose = function(t) {
        var e = this;
        if (this.connectionStarted) {
            this.connectionState = b.Disconnected,
            this.connectionStarted = !1;
            try {
                this.closedCallbacks.forEach(function(r) {
                    return r.apply(e, [t])
                })
            } catch (r) {
                this.logger.log(l.Error, "An onclose callback called with error '" + t + "' threw error '" + r + "'.")
            }
        }
    }
    ,
    o.prototype.reconnect = function(t) {
        return _(this, void 0, void 0, function() {
            var e, r, i, n, c, a = this;
            return D(this, function(u) {
                switch (u.label) {
                case 0:
                    if (e = Date.now(),
                    r = 0,
                    i = t !== void 0 ? t : new Error("Attempting to reconnect due to a unknown error."),
                    n = this.getNextRetryDelay(r++, 0, i),
                    n === null)
                        return this.logger.log(l.Debug, "Connection not reconnecting because the IRetryPolicy returned null on the first reconnect attempt."),
                        this.completeClose(t),
                        [2];
                    if (this.connectionState = b.Reconnecting,
                    t ? this.logger.log(l.Information, "Connection reconnecting because of error '" + t + "'.") : this.logger.log(l.Information, "Connection reconnecting."),
                    this.onreconnecting) {
                        try {
                            this.reconnectingCallbacks.forEach(function(s) {
                                return s.apply(a, [t])
                            })
                        } catch (s) {
                            this.logger.log(l.Error, "An onreconnecting callback called with error '" + t + "' threw error '" + s + "'.")
                        }
                        if (this.connectionState !== b.Reconnecting)
                            return this.logger.log(l.Debug, "Connection left the reconnecting state in onreconnecting callback. Done reconnecting."),
                            [2]
                    }
                    u.label = 1;
                case 1:
                    return n === null ? [3, 7] : (this.logger.log(l.Information, "Reconnect attempt number " + r + " will start in " + n + " ms."),
                    [4, new Promise(function(s) {
                        a.reconnectDelayHandle = setTimeout(s, n)
                    }
                    )]);
                case 2:
                    if (u.sent(),
                    this.reconnectDelayHandle = void 0,
                    this.connectionState !== b.Reconnecting)
                        return this.logger.log(l.Debug, "Connection left the reconnecting state during reconnect delay. Done reconnecting."),
                        [2];
                    u.label = 3;
                case 3:
                    return u.trys.push([3, 5, , 6]),
                    [4, this.startInternal()];
                case 4:
                    if (u.sent(),
                    this.connectionState = b.Connected,
                    this.logger.log(l.Information, "HubConnection reconnected successfully."),
                    this.onreconnected)
                        try {
                            this.reconnectedCallbacks.forEach(function(s) {
                                return s.apply(a, [a.connection.connectionId])
                            })
                        } catch (s) {
                            this.logger.log(l.Error, "An onreconnected callback called with connectionId '" + this.connection.connectionId + "; threw error '" + s + "'.")
                        }
                    return [2];
                case 5:
                    return c = u.sent(),
                    this.logger.log(l.Information, "Reconnect attempt failed because of error '" + c + "'."),
                    this.connectionState !== b.Reconnecting ? (this.logger.log(l.Debug, "Connection moved to the '" + this.connectionState + "' from the reconnecting state during reconnect attempt. Done reconnecting."),
                    this.connectionState === b.Disconnecting && this.completeClose(),
                    [2]) : (i = c instanceof Error ? c : new Error(c.toString()),
                    n = this.getNextRetryDelay(r++, Date.now() - e, i),
                    [3, 6]);
                case 6:
                    return [3, 1];
                case 7:
                    return this.logger.log(l.Information, "Reconnect retries have been exhausted after " + (Date.now() - e) + " ms and " + r + " failed attempts. Connection disconnecting."),
                    this.completeClose(),
                    [2]
                }
            })
        })
    }
    ,
    o.prototype.getNextRetryDelay = function(t, e, r) {
        try {
            return this.reconnectPolicy.nextRetryDelayInMilliseconds({
                elapsedMilliseconds: e,
                previousRetryCount: t,
                retryReason: r
            })
        } catch (i) {
            return this.logger.log(l.Error, "IRetryPolicy.nextRetryDelayInMilliseconds(" + t + ", " + e + ") threw error '" + i + "'."),
            null
        }
    }
    ,
    o.prototype.cancelCallbacksWithError = function(t) {
        var e = this.callbacks;
        this.callbacks = {},
        Object.keys(e).forEach(function(r) {
            var i = e[r];
            i(null, t)
        })
    }
    ,
    o.prototype.cleanupPingTimer = function() {
        this.pingServerHandle && (clearTimeout(this.pingServerHandle),
        this.pingServerHandle = void 0)
    }
    ,
    o.prototype.cleanupTimeout = function() {
        this.timeoutHandle && clearTimeout(this.timeoutHandle)
    }
    ,
    o.prototype.createInvocation = function(t, e, r, i) {
        if (r)
            return i.length !== 0 ? {
                arguments: e,
                streamIds: i,
                target: t,
                type: g.Invocation
            } : {
                arguments: e,
                target: t,
                type: g.Invocation
            };
        var n = this.invocationId;
        return this.invocationId++,
        i.length !== 0 ? {
            arguments: e,
            invocationId: n.toString(),
            streamIds: i,
            target: t,
            type: g.Invocation
        } : {
            arguments: e,
            invocationId: n.toString(),
            target: t,
            type: g.Invocation
        }
    }
    ,
    o.prototype.launchStreams = function(t, e) {
        var r = this;
        if (t.length !== 0) {
            e || (e = Promise.resolve());
            var i = function(c) {
                t[c].subscribe({
                    complete: function() {
                        e = e.then(function() {
                            return r.sendWithProtocol(r.createCompletionMessage(c))
                        })
                    },
                    error: function(a) {
                        var u;
                        a instanceof Error ? u = a.message : a && a.toString ? u = a.toString() : u = "Unknown error",
                        e = e.then(function() {
                            return r.sendWithProtocol(r.createCompletionMessage(c, u))
                        })
                    },
                    next: function(a) {
                        e = e.then(function() {
                            return r.sendWithProtocol(r.createStreamItemMessage(c, a))
                        })
                    }
                })
            };
            for (var n in t)
                i(n)
        }
    }
    ,
    o.prototype.replaceStreamingParams = function(t) {
        for (var e = [], r = [], i = 0; i < t.length; i++) {
            var n = t[i];
            if (this.isObservable(n)) {
                var c = this.invocationId;
                this.invocationId++,
                e[c] = n,
                r.push(c.toString()),
                t.splice(i, 1)
            }
        }
        return [e, r]
    }
    ,
    o.prototype.isObservable = function(t) {
        return t && t.subscribe && typeof t.subscribe == "function"
    }
    ,
    o.prototype.createStreamInvocation = function(t, e, r) {
        var i = this.invocationId;
        return this.invocationId++,
        r.length !== 0 ? {
            arguments: e,
            invocationId: i.toString(),
            streamIds: r,
            target: t,
            type: g.StreamInvocation
        } : {
            arguments: e,
            invocationId: i.toString(),
            target: t,
            type: g.StreamInvocation
        }
    }
    ,
    o.prototype.createCancelInvocation = function(t) {
        return {
            invocationId: t,
            type: g.CancelInvocation
        }
    }
    ,
    o.prototype.createStreamItemMessage = function(t, e) {
        return {
            invocationId: t,
            item: e,
            type: g.StreamItem
        }
    }
    ,
    o.prototype.createCompletionMessage = function(t, e, r) {
        return e ? {
            error: e,
            invocationId: t,
            type: g.Completion
        } : {
            invocationId: t,
            result: r,
            type: g.Completion
        }
    }
    ,
    o
}
)(), Pe = [0, 2e3, 1e4, 3e4, null], X = (function() {
    function o(t) {
        this.retryDelays = t !== void 0 ? t.concat([null]) : Pe
    }
    return o.prototype.nextRetryDelayInMilliseconds = function(t) {
        return this.retryDelays[t.previousRetryCount]
    }
    ,
    o
}
)(), m;
(function(o) {
    o[o.None = 0] = "None",
    o[o.WebSockets = 1] = "WebSockets",
    o[o.ServerSentEvents = 2] = "ServerSentEvents",
    o[o.LongPolling = 4] = "LongPolling"
}
)(m || (m = {}));
var S;
(function(o) {
    o[o.Text = 1] = "Text",
    o[o.Binary = 2] = "Binary"
}
)(S || (S = {}));
var Te = (function() {
    function o() {
        this.isAborted = !1,
        this.onabort = null
    }
    return o.prototype.abort = function() {
        this.isAborted || (this.isAborted = !0,
        this.onabort && this.onabort())
    }
    ,
    Object.defineProperty(o.prototype, "signal", {
        get: function() {
            return this
        },
        enumerable: !0,
        configurable: !0
    }),
    Object.defineProperty(o.prototype, "aborted", {
        get: function() {
            return this.isAborted
        },
        enumerable: !0,
        configurable: !0
    }),
    o
}
)()
  , J = Object.assign || function(o) {
    for (var t, e = 1, r = arguments.length; e < r; e++) {
        t = arguments[e];
        for (var i in t)
            Object.prototype.hasOwnProperty.call(t, i) && (o[i] = t[i])
    }
    return o
}
  , x = function(o, t, e, r) {
    return new (e || (e = Promise))(function(i, n) {
        function c(s) {
            try {
                u(r.next(s))
            } catch (h) {
                n(h)
            }
        }
        function a(s) {
            try {
                u(r.throw(s))
            } catch (h) {
                n(h)
            }
        }
        function u(s) {
            s.done ? i(s.value) : new e(function(h) {
                h(s.value)
            }
            ).then(c, a)
        }
        u((r = r.apply(o, t || [])).next())
    }
    )
}
  , R = function(o, t) {
    var e = {
        label: 0,
        sent: function() {
            if (n[0] & 1)
                throw n[1];
            return n[1]
        },
        trys: [],
        ops: []
    }, r, i, n, c;
    return c = {
        next: a(0),
        throw: a(1),
        return: a(2)
    },
    typeof Symbol == "function" && (c[Symbol.iterator] = function() {
        return this
    }
    ),
    c;
    function a(s) {
        return function(h) {
            return u([s, h])
        }
    }
    function u(s) {
        if (r)
            throw new TypeError("Generator is already executing.");
        for (; e; )
            try {
                if (r = 1,
                i && (n = s[0] & 2 ? i.return : s[0] ? i.throw || ((n = i.return) && n.call(i),
                0) : i.next) && !(n = n.call(i, s[1])).done)
                    return n;
                switch (i = 0,
                n && (s = [s[0] & 2, n.value]),
                s[0]) {
                case 0:
                case 1:
                    n = s;
                    break;
                case 4:
                    return e.label++,
                    {
                        value: s[1],
                        done: !1
                    };
                case 5:
                    e.label++,
                    i = s[1],
                    s = [0];
                    continue;
                case 7:
                    s = e.ops.pop(),
                    e.trys.pop();
                    continue;
                default:
                    if (n = e.trys,
                    !(n = n.length > 0 && n[n.length - 1]) && (s[0] === 6 || s[0] === 2)) {
                        e = 0;
                        continue
                    }
                    if (s[0] === 3 && (!n || s[1] > n[0] && s[1] < n[3])) {
                        e.label = s[1];
                        break
                    }
                    if (s[0] === 6 && e.label < n[1]) {
                        e.label = n[1],
                        n = s;
                        break
                    }
                    if (n && e.label < n[2]) {
                        e.label = n[2],
                        e.ops.push(s);
                        break
                    }
                    n[2] && e.ops.pop(),
                    e.trys.pop();
                    continue
                }
                s = t.call(o, e)
            } catch (h) {
                s = [6, h],
                i = 0
            } finally {
                r = n = 0
            }
        if (s[0] & 5)
            throw s[1];
        return {
            value: s[0] ? s[1] : void 0,
            done: !0
        }
    }
}
  , V = (function() {
    function o(t, e, r, i, n, c) {
        this.httpClient = t,
        this.accessTokenFactory = e,
        this.logger = r,
        this.pollAbort = new Te,
        this.logMessageContent = i,
        this.withCredentials = n,
        this.headers = c,
        this.running = !1,
        this.onreceive = null,
        this.onclose = null
    }
    return Object.defineProperty(o.prototype, "pollAborted", {
        get: function() {
            return this.pollAbort.aborted
        },
        enumerable: !0,
        configurable: !0
    }),
    o.prototype.connect = function(t, e) {
        return x(this, void 0, void 0, function() {
            var r, i, n, c, a, u, s, h, f;
            return R(this, function(d) {
                switch (d.label) {
                case 0:
                    if (w.isRequired(t, "url"),
                    w.isRequired(e, "transferFormat"),
                    w.isIn(e, S, "transferFormat"),
                    this.url = t,
                    this.logger.log(l.Trace, "(LongPolling transport) Connecting."),
                    e === S.Binary && typeof XMLHttpRequest < "u" && typeof new XMLHttpRequest().responseType != "string")
                        throw new Error("Binary protocols over XmlHttpRequest not implementing advanced features are not supported.");
                    return i = I(),
                    n = i[0],
                    c = i[1],
                    a = J((r = {},
                    r[n] = c,
                    r), this.headers),
                    u = {
                        abortSignal: this.pollAbort.signal,
                        headers: a,
                        timeout: 1e5,
                        withCredentials: this.withCredentials
                    },
                    e === S.Binary && (u.responseType = "arraybuffer"),
                    [4, this.getAccessToken()];
                case 1:
                    return s = d.sent(),
                    this.updateHeaderToken(u, s),
                    h = t + "&_=" + Date.now(),
                    this.logger.log(l.Trace, "(LongPolling transport) polling: " + h + "."),
                    [4, this.httpClient.get(h, u)];
                case 2:
                    return f = d.sent(),
                    f.statusCode !== 200 ? (this.logger.log(l.Error, "(LongPolling transport) Unexpected response code: " + f.statusCode + "."),
                    this.closeError = new O(f.statusText || "",f.statusCode),
                    this.running = !1) : this.running = !0,
                    this.receiving = this.poll(this.url, u),
                    [2]
                }
            })
        })
    }
    ,
    o.prototype.getAccessToken = function() {
        return x(this, void 0, void 0, function() {
            return R(this, function(t) {
                switch (t.label) {
                case 0:
                    return this.accessTokenFactory ? [4, this.accessTokenFactory()] : [3, 2];
                case 1:
                    return [2, t.sent()];
                case 2:
                    return [2, null]
                }
            })
        })
    }
    ,
    o.prototype.updateHeaderToken = function(t, e) {
        if (t.headers || (t.headers = {}),
        e) {
            t.headers.Authorization = "Bearer " + e;
            return
        }
        t.headers.Authorization && delete t.headers.Authorization
    }
    ,
    o.prototype.poll = function(t, e) {
        return x(this, void 0, void 0, function() {
            var r, i, n, c;
            return R(this, function(a) {
                switch (a.label) {
                case 0:
                    a.trys.push([0, , 8, 9]),
                    a.label = 1;
                case 1:
                    return this.running ? [4, this.getAccessToken()] : [3, 7];
                case 2:
                    r = a.sent(),
                    this.updateHeaderToken(e, r),
                    a.label = 3;
                case 3:
                    return a.trys.push([3, 5, , 6]),
                    i = t + "&_=" + Date.now(),
                    this.logger.log(l.Trace, "(LongPolling transport) polling: " + i + "."),
                    [4, this.httpClient.get(i, e)];
                case 4:
                    return n = a.sent(),
                    n.statusCode === 204 ? (this.logger.log(l.Information, "(LongPolling transport) Poll terminated by server."),
                    this.running = !1) : n.statusCode !== 200 ? (this.logger.log(l.Error, "(LongPolling transport) Unexpected response code: " + n.statusCode + "."),
                    this.closeError = new O(n.statusText || "",n.statusCode),
                    this.running = !1) : n.content ? (this.logger.log(l.Trace, "(LongPolling transport) data received. " + j(n.content, this.logMessageContent) + "."),
                    this.onreceive && this.onreceive(n.content)) : this.logger.log(l.Trace, "(LongPolling transport) Poll timed out, reissuing."),
                    [3, 6];
                case 5:
                    return c = a.sent(),
                    this.running ? c instanceof L ? this.logger.log(l.Trace, "(LongPolling transport) Poll timed out, reissuing.") : (this.closeError = c,
                    this.running = !1) : this.logger.log(l.Trace, "(LongPolling transport) Poll errored after shutdown: " + c.message),
                    [3, 6];
                case 6:
                    return [3, 1];
                case 7:
                    return [3, 9];
                case 8:
                    return this.logger.log(l.Trace, "(LongPolling transport) Polling complete."),
                    this.pollAborted || this.raiseOnClose(),
                    [7];
                case 9:
                    return [2]
                }
            })
        })
    }
    ,
    o.prototype.send = function(t) {
        return x(this, void 0, void 0, function() {
            return R(this, function(e) {
                return this.running ? [2, Z(this.logger, "LongPolling", this.httpClient, this.url, this.accessTokenFactory, t, this.logMessageContent, this.withCredentials, this.headers)] : [2, Promise.reject(new Error("Cannot send until the transport is connected"))]
            })
        })
    }
    ,
    o.prototype.stop = function() {
        return x(this, void 0, void 0, function() {
            var t, e, r, i, n, c;
            return R(this, function(a) {
                switch (a.label) {
                case 0:
                    this.logger.log(l.Trace, "(LongPolling transport) Stopping polling."),
                    this.running = !1,
                    this.pollAbort.abort(),
                    a.label = 1;
                case 1:
                    return a.trys.push([1, , 5, 6]),
                    [4, this.receiving];
                case 2:
                    return a.sent(),
                    this.logger.log(l.Trace, "(LongPolling transport) sending DELETE request to " + this.url + "."),
                    t = {},
                    e = I(),
                    r = e[0],
                    i = e[1],
                    t[r] = i,
                    n = {
                        headers: J({}, t, this.headers),
                        withCredentials: this.withCredentials
                    },
                    [4, this.getAccessToken()];
                case 3:
                    return c = a.sent(),
                    this.updateHeaderToken(n, c),
                    [4, this.httpClient.delete(this.url, n)];
                case 4:
                    return a.sent(),
                    this.logger.log(l.Trace, "(LongPolling transport) DELETE request sent."),
                    [3, 6];
                case 5:
                    return this.logger.log(l.Trace, "(LongPolling transport) Stop finished."),
                    this.raiseOnClose(),
                    [7];
                case 6:
                    return [2]
                }
            })
        })
    }
    ,
    o.prototype.raiseOnClose = function() {
        if (this.onclose) {
            var t = "(LongPolling transport) Firing onclose event.";
            this.closeError && (t += " Error: " + this.closeError),
            this.logger.log(l.Trace, t),
            this.onclose(this.closeError)
        }
    }
    ,
    o
}
)()
  , Ie = Object.assign || function(o) {
    for (var t, e = 1, r = arguments.length; e < r; e++) {
        t = arguments[e];
        for (var i in t)
            Object.prototype.hasOwnProperty.call(t, i) && (o[i] = t[i])
    }
    return o
}
  , G = function(o, t, e, r) {
    return new (e || (e = Promise))(function(i, n) {
        function c(s) {
            try {
                u(r.next(s))
            } catch (h) {
                n(h)
            }
        }
        function a(s) {
            try {
                u(r.throw(s))
            } catch (h) {
                n(h)
            }
        }
        function u(s) {
            s.done ? i(s.value) : new e(function(h) {
                h(s.value)
            }
            ).then(c, a)
        }
        u((r = r.apply(o, t || [])).next())
    }
    )
}
  , K = function(o, t) {
    var e = {
        label: 0,
        sent: function() {
            if (n[0] & 1)
                throw n[1];
            return n[1]
        },
        trys: [],
        ops: []
    }, r, i, n, c;
    return c = {
        next: a(0),
        throw: a(1),
        return: a(2)
    },
    typeof Symbol == "function" && (c[Symbol.iterator] = function() {
        return this
    }
    ),
    c;
    function a(s) {
        return function(h) {
            return u([s, h])
        }
    }
    function u(s) {
        if (r)
            throw new TypeError("Generator is already executing.");
        for (; e; )
            try {
                if (r = 1,
                i && (n = s[0] & 2 ? i.return : s[0] ? i.throw || ((n = i.return) && n.call(i),
                0) : i.next) && !(n = n.call(i, s[1])).done)
                    return n;
                switch (i = 0,
                n && (s = [s[0] & 2, n.value]),
                s[0]) {
                case 0:
                case 1:
                    n = s;
                    break;
                case 4:
                    return e.label++,
                    {
                        value: s[1],
                        done: !1
                    };
                case 5:
                    e.label++,
                    i = s[1],
                    s = [0];
                    continue;
                case 7:
                    s = e.ops.pop(),
                    e.trys.pop();
                    continue;
                default:
                    if (n = e.trys,
                    !(n = n.length > 0 && n[n.length - 1]) && (s[0] === 6 || s[0] === 2)) {
                        e = 0;
                        continue
                    }
                    if (s[0] === 3 && (!n || s[1] > n[0] && s[1] < n[3])) {
                        e.label = s[1];
                        break
                    }
                    if (s[0] === 6 && e.label < n[1]) {
                        e.label = n[1],
                        n = s;
                        break
                    }
                    if (n && e.label < n[2]) {
                        e.label = n[2],
                        e.ops.push(s);
                        break
                    }
                    n[2] && e.ops.pop(),
                    e.trys.pop();
                    continue
                }
                s = t.call(o, e)
            } catch (h) {
                s = [6, h],
                i = 0
            } finally {
                r = n = 0
            }
        if (s[0] & 5)
            throw s[1];
        return {
            value: s[0] ? s[1] : void 0,
            done: !0
        }
    }
}
  , _e = (function() {
    function o(t, e, r, i, n, c, a) {
        this.httpClient = t,
        this.accessTokenFactory = e,
        this.logger = r,
        this.logMessageContent = i,
        this.withCredentials = c,
        this.eventSourceConstructor = n,
        this.headers = a,
        this.onreceive = null,
        this.onclose = null
    }
    return o.prototype.connect = function(t, e) {
        return G(this, void 0, void 0, function() {
            var r, i = this;
            return K(this, function(n) {
                switch (n.label) {
                case 0:
                    return w.isRequired(t, "url"),
                    w.isRequired(e, "transferFormat"),
                    w.isIn(e, S, "transferFormat"),
                    this.logger.log(l.Trace, "(SSE transport) Connecting."),
                    this.url = t,
                    this.accessTokenFactory ? [4, this.accessTokenFactory()] : [3, 2];
                case 1:
                    r = n.sent(),
                    r && (t += (t.indexOf("?") < 0 ? "?" : "&") + ("access_token=" + encodeURIComponent(r))),
                    n.label = 2;
                case 2:
                    return [2, new Promise(function(c, a) {
                        var u = !1;
                        if (e !== S.Text) {
                            a(new Error("The Server-Sent Events transport only supports the 'Text' transfer format"));
                            return
                        }
                        var s;
                        if (C.isBrowser || C.isWebWorker)
                            s = new i.eventSourceConstructor(t,{
                                withCredentials: i.withCredentials
                            });
                        else {
                            var h = i.httpClient.getCookieString(t)
                              , f = {};
                            f.Cookie = h;
                            var d = I()
                              , y = d[0]
                              , k = d[1];
                            f[y] = k,
                            s = new i.eventSourceConstructor(t,{
                                withCredentials: i.withCredentials,
                                headers: Ie({}, f, i.headers)
                            })
                        }
                        try {
                            s.onmessage = function(v) {
                                if (i.onreceive)
                                    try {
                                        i.logger.log(l.Trace, "(SSE transport) data received. " + j(v.data, i.logMessageContent) + "."),
                                        i.onreceive(v.data)
                                    } catch (p) {
                                        i.close(p);
                                        return
                                    }
                            }
                            ,
                            s.onerror = function(v) {
                                var p = new Error(v.data || "Error occurred");
                                u ? i.close(p) : a(p)
                            }
                            ,
                            s.onopen = function() {
                                i.logger.log(l.Information, "SSE connected to " + i.url),
                                i.eventSource = s,
                                u = !0,
                                c()
                            }
                        } catch (v) {
                            a(v);
                            return
                        }
                    }
                    )]
                }
            })
        })
    }
    ,
    o.prototype.send = function(t) {
        return G(this, void 0, void 0, function() {
            return K(this, function(e) {
                return this.eventSource ? [2, Z(this.logger, "SSE", this.httpClient, this.url, this.accessTokenFactory, t, this.logMessageContent, this.withCredentials, this.headers)] : [2, Promise.reject(new Error("Cannot send until the transport is connected"))]
            })
        })
    }
    ,
    o.prototype.stop = function() {
        return this.close(),
        Promise.resolve()
    }
    ,
    o.prototype.close = function(t) {
        this.eventSource && (this.eventSource.close(),
        this.eventSource = void 0,
        this.onclose && this.onclose(t))
    }
    ,
    o
}
)()
  , De = Object.assign || function(o) {
    for (var t, e = 1, r = arguments.length; e < r; e++) {
        t = arguments[e];
        for (var i in t)
            Object.prototype.hasOwnProperty.call(t, i) && (o[i] = t[i])
    }
    return o
}
  , xe = function(o, t, e, r) {
    return new (e || (e = Promise))(function(i, n) {
        function c(s) {
            try {
                u(r.next(s))
            } catch (h) {
                n(h)
            }
        }
        function a(s) {
            try {
                u(r.throw(s))
            } catch (h) {
                n(h)
            }
        }
        function u(s) {
            s.done ? i(s.value) : new e(function(h) {
                h(s.value)
            }
            ).then(c, a)
        }
        u((r = r.apply(o, t || [])).next())
    }
    )
}
  , Re = function(o, t) {
    var e = {
        label: 0,
        sent: function() {
            if (n[0] & 1)
                throw n[1];
            return n[1]
        },
        trys: [],
        ops: []
    }, r, i, n, c;
    return c = {
        next: a(0),
        throw: a(1),
        return: a(2)
    },
    typeof Symbol == "function" && (c[Symbol.iterator] = function() {
        return this
    }
    ),
    c;
    function a(s) {
        return function(h) {
            return u([s, h])
        }
    }
    function u(s) {
        if (r)
            throw new TypeError("Generator is already executing.");
        for (; e; )
            try {
                if (r = 1,
                i && (n = s[0] & 2 ? i.return : s[0] ? i.throw || ((n = i.return) && n.call(i),
                0) : i.next) && !(n = n.call(i, s[1])).done)
                    return n;
                switch (i = 0,
                n && (s = [s[0] & 2, n.value]),
                s[0]) {
                case 0:
                case 1:
                    n = s;
                    break;
                case 4:
                    return e.label++,
                    {
                        value: s[1],
                        done: !1
                    };
                case 5:
                    e.label++,
                    i = s[1],
                    s = [0];
                    continue;
                case 7:
                    s = e.ops.pop(),
                    e.trys.pop();
                    continue;
                default:
                    if (n = e.trys,
                    !(n = n.length > 0 && n[n.length - 1]) && (s[0] === 6 || s[0] === 2)) {
                        e = 0;
                        continue
                    }
                    if (s[0] === 3 && (!n || s[1] > n[0] && s[1] < n[3])) {
                        e.label = s[1];
                        break
                    }
                    if (s[0] === 6 && e.label < n[1]) {
                        e.label = n[1],
                        n = s;
                        break
                    }
                    if (n && e.label < n[2]) {
                        e.label = n[2],
                        e.ops.push(s);
                        break
                    }
                    n[2] && e.ops.pop(),
                    e.trys.pop();
                    continue
                }
                s = t.call(o, e)
            } catch (h) {
                s = [6, h],
                i = 0
            } finally {
                r = n = 0
            }
        if (s[0] & 5)
            throw s[1];
        return {
            value: s[0] ? s[1] : void 0,
            done: !0
        }
    }
}
  , Oe = (function() {
    function o(t, e, r, i, n, c) {
        this.logger = r,
        this.accessTokenFactory = e,
        this.logMessageContent = i,
        this.webSocketConstructor = n,
        this.httpClient = t,
        this.onreceive = null,
        this.onclose = null,
        this.headers = c
    }
    return o.prototype.connect = function(t, e) {
        return xe(this, void 0, void 0, function() {
            var r, i = this;
            return Re(this, function(n) {
                switch (n.label) {
                case 0:
                    return w.isRequired(t, "url"),
                    w.isRequired(e, "transferFormat"),
                    w.isIn(e, S, "transferFormat"),
                    this.logger.log(l.Trace, "(WebSockets transport) Connecting."),
                    this.accessTokenFactory ? [4, this.accessTokenFactory()] : [3, 2];
                case 1:
                    r = n.sent(),
                    r && (t += (t.indexOf("?") < 0 ? "?" : "&") + ("access_token=" + encodeURIComponent(r))),
                    n.label = 2;
                case 2:
                    return [2, new Promise(function(c, a) {
                        t = t.replace(/^http/, "ws");
                        var u, s = i.httpClient.getCookieString(t), h = !1;
                        if (C.isNode) {
                            var f = {}
                              , d = I()
                              , y = d[0]
                              , k = d[1];
                            f[y] = k,
                            s && (f.Cookie = "" + s),
                            u = new i.webSocketConstructor(t,void 0,{
                                headers: De({}, f, i.headers)
                            })
                        }
                        u || (u = new i.webSocketConstructor(t)),
                        e === S.Binary && (u.binaryType = "arraybuffer"),
                        u.onopen = function(v) {
                            i.logger.log(l.Information, "WebSocket connected to " + t + "."),
                            i.webSocket = u,
                            h = !0,
                            c()
                        }
                        ,
                        u.onerror = function(v) {
                            var p = null;
                            typeof ErrorEvent < "u" && v instanceof ErrorEvent ? p = v.error : p = new Error("There was an error with the transport."),
                            a(p)
                        }
                        ,
                        u.onmessage = function(v) {
                            if (i.logger.log(l.Trace, "(WebSockets transport) data received. " + j(v.data, i.logMessageContent) + "."),
                            i.onreceive)
                                try {
                                    i.onreceive(v.data)
                                } catch (p) {
                                    i.close(p);
                                    return
                                }
                        }
                        ,
                        u.onclose = function(v) {
                            if (h)
                                i.close(v);
                            else {
                                var p = null;
                                typeof ErrorEvent < "u" && v instanceof ErrorEvent ? p = v.error : p = new Error("There was an error with the transport."),
                                a(p)
                            }
                        }
                    }
                    )]
                }
            })
        })
    }
    ,
    o.prototype.send = function(t) {
        return this.webSocket && this.webSocket.readyState === this.webSocketConstructor.OPEN ? (this.logger.log(l.Trace, "(WebSockets transport) sending data. " + j(t, this.logMessageContent) + "."),
        this.webSocket.send(t),
        Promise.resolve()) : Promise.reject("WebSocket is not in the OPEN state")
    }
    ,
    o.prototype.stop = function() {
        return this.webSocket && this.close(void 0),
        Promise.resolve()
    }
    ,
    o.prototype.close = function(t) {
        this.webSocket && (this.webSocket.onclose = function() {}
        ,
        this.webSocket.onmessage = function() {}
        ,
        this.webSocket.onerror = function() {}
        ,
        this.webSocket.close(),
        this.webSocket = void 0),
        this.logger.log(l.Trace, "(WebSockets transport) socket closed."),
        this.onclose && (this.isCloseEvent(t) && (t.wasClean === !1 || t.code !== 1e3) ? this.onclose(new Error("WebSocket closed with status code: " + t.code + " (" + t.reason + ").")) : t instanceof Error ? this.onclose(t) : this.onclose())
    }
    ,
    o.prototype.isCloseEvent = function(t) {
        return t && typeof t.wasClean == "boolean" && typeof t.code == "number"
    }
    ,
    o
}
)()
  , He = Object.assign || function(o) {
    for (var t, e = 1, r = arguments.length; e < r; e++) {
        t = arguments[e];
        for (var i in t)
            Object.prototype.hasOwnProperty.call(t, i) && (o[i] = t[i])
    }
    return o
}
  , P = function(o, t, e, r) {
    return new (e || (e = Promise))(function(i, n) {
        function c(s) {
            try {
                u(r.next(s))
            } catch (h) {
                n(h)
            }
        }
        function a(s) {
            try {
                u(r.throw(s))
            } catch (h) {
                n(h)
            }
        }
        function u(s) {
            s.done ? i(s.value) : new e(function(h) {
                h(s.value)
            }
            ).then(c, a)
        }
        u((r = r.apply(o, t || [])).next())
    }
    )
}
  , E = function(o, t) {
    var e = {
        label: 0,
        sent: function() {
            if (n[0] & 1)
                throw n[1];
            return n[1]
        },
        trys: [],
        ops: []
    }, r, i, n, c;
    return c = {
        next: a(0),
        throw: a(1),
        return: a(2)
    },
    typeof Symbol == "function" && (c[Symbol.iterator] = function() {
        return this
    }
    ),
    c;
    function a(s) {
        return function(h) {
            return u([s, h])
        }
    }
    function u(s) {
        if (r)
            throw new TypeError("Generator is already executing.");
        for (; e; )
            try {
                if (r = 1,
                i && (n = s[0] & 2 ? i.return : s[0] ? i.throw || ((n = i.return) && n.call(i),
                0) : i.next) && !(n = n.call(i, s[1])).done)
                    return n;
                switch (i = 0,
                n && (s = [s[0] & 2, n.value]),
                s[0]) {
                case 0:
                case 1:
                    n = s;
                    break;
                case 4:
                    return e.label++,
                    {
                        value: s[1],
                        done: !1
                    };
                case 5:
                    e.label++,
                    i = s[1],
                    s = [0];
                    continue;
                case 7:
                    s = e.ops.pop(),
                    e.trys.pop();
                    continue;
                default:
                    if (n = e.trys,
                    !(n = n.length > 0 && n[n.length - 1]) && (s[0] === 6 || s[0] === 2)) {
                        e = 0;
                        continue
                    }
                    if (s[0] === 3 && (!n || s[1] > n[0] && s[1] < n[3])) {
                        e.label = s[1];
                        break
                    }
                    if (s[0] === 6 && e.label < n[1]) {
                        e.label = n[1],
                        n = s;
                        break
                    }
                    if (n && e.label < n[2]) {
                        e.label = n[2],
                        e.ops.push(s);
                        break
                    }
                    n[2] && e.ops.pop(),
                    e.trys.pop();
                    continue
                }
                s = t.call(o, e)
            } catch (h) {
                s = [6, h],
                i = 0
            } finally {
                r = n = 0
            }
        if (s[0] & 5)
            throw s[1];
        return {
            value: s[0] ? s[1] : void 0,
            done: !0
        }
    }
}
  , z = 100
  , je = (function() {
    function o(t, e) {
        if (e === void 0 && (e = {}),
        this.stopPromiseResolver = function() {}
        ,
        this.features = {},
        this.negotiateVersion = 1,
        w.isRequired(t, "url"),
        this.logger = oe(e.logger),
        this.baseUrl = this.resolveUrl(t),
        e = e || {},
        e.logMessageContent = e.logMessageContent === void 0 ? !1 : e.logMessageContent,
        typeof e.withCredentials == "boolean" || e.withCredentials === void 0)
            e.withCredentials = e.withCredentials === void 0 ? !0 : e.withCredentials;
        else
            throw new Error("withCredentials option was not a 'boolean' or 'undefined' value");
        var r = null
          , i = null;
        if (C.isNode && typeof require < "u") {
            var n = typeof __webpack_require__ == "function" ? __non_webpack_require__ : require;
            r = n("ws"),
            i = n("eventsource")
        }
        !C.isNode && typeof WebSocket < "u" && !e.WebSocket ? e.WebSocket = WebSocket : C.isNode && !e.WebSocket && r && (e.WebSocket = r),
        !C.isNode && typeof EventSource < "u" && !e.EventSource ? e.EventSource = EventSource : C.isNode && !e.EventSource && typeof i < "u" && (e.EventSource = i),
        this.httpClient = e.httpClient || new we(this.logger),
        this.connectionState = "Disconnected",
        this.connectionStarted = !1,
        this.options = e,
        this.onreceive = null,
        this.onclose = null
    }
    return o.prototype.start = function(t) {
        return P(this, void 0, void 0, function() {
            var e, e;
            return E(this, function(r) {
                switch (r.label) {
                case 0:
                    return t = t || S.Binary,
                    w.isIn(t, S, "transferFormat"),
                    this.logger.log(l.Debug, "Starting connection with transfer format '" + S[t] + "'."),
                    this.connectionState !== "Disconnected" ? [2, Promise.reject(new Error("Cannot start an HttpConnection that is not in the 'Disconnected' state."))] : (this.connectionState = "Connecting",
                    this.startInternalPromise = this.startInternal(t),
                    [4, this.startInternalPromise]);
                case 1:
                    return r.sent(),
                    this.connectionState !== "Disconnecting" ? [3, 3] : (e = "Failed to start the HttpConnection before stop() was called.",
                    this.logger.log(l.Error, e),
                    [4, this.stopPromise]);
                case 2:
                    return r.sent(),
                    [2, Promise.reject(new Error(e))];
                case 3:
                    if (this.connectionState !== "Connected")
                        return e = "HttpConnection.startInternal completed gracefully but didn't enter the connection into the connected state!",
                        this.logger.log(l.Error, e),
                        [2, Promise.reject(new Error(e))];
                    r.label = 4;
                case 4:
                    return this.connectionStarted = !0,
                    [2]
                }
            })
        })
    }
    ,
    o.prototype.send = function(t) {
        return this.connectionState !== "Connected" ? Promise.reject(new Error("Cannot send data if the connection is not in the 'Connected' State.")) : (this.sendQueue || (this.sendQueue = new We(this.transport)),
        this.sendQueue.send(t))
    }
    ,
    o.prototype.stop = function(t) {
        return P(this, void 0, void 0, function() {
            var e = this;
            return E(this, function(r) {
                switch (r.label) {
                case 0:
                    return this.connectionState === "Disconnected" ? (this.logger.log(l.Debug, "Call to HttpConnection.stop(" + t + ") ignored because the connection is already in the disconnected state."),
                    [2, Promise.resolve()]) : this.connectionState === "Disconnecting" ? (this.logger.log(l.Debug, "Call to HttpConnection.stop(" + t + ") ignored because the connection is already in the disconnecting state."),
                    [2, this.stopPromise]) : (this.connectionState = "Disconnecting",
                    this.stopPromise = new Promise(function(i) {
                        e.stopPromiseResolver = i
                    }
                    ),
                    [4, this.stopInternal(t)]);
                case 1:
                    return r.sent(),
                    [4, this.stopPromise];
                case 2:
                    return r.sent(),
                    [2]
                }
            })
        })
    }
    ,
    o.prototype.stopInternal = function(t) {
        return P(this, void 0, void 0, function() {
            var e;
            return E(this, function(r) {
                switch (r.label) {
                case 0:
                    this.stopError = t,
                    r.label = 1;
                case 1:
                    return r.trys.push([1, 3, , 4]),
                    [4, this.startInternalPromise];
                case 2:
                    return r.sent(),
                    [3, 4];
                case 3:
                    return r.sent(),
                    [3, 4];
                case 4:
                    if (!this.transport)
                        return [3, 9];
                    r.label = 5;
                case 5:
                    return r.trys.push([5, 7, , 8]),
                    [4, this.transport.stop()];
                case 6:
                    return r.sent(),
                    [3, 8];
                case 7:
                    return e = r.sent(),
                    this.logger.log(l.Error, "HttpConnection.transport.stop() threw error '" + e + "'."),
                    this.stopConnection(),
                    [3, 8];
                case 8:
                    return this.transport = void 0,
                    [3, 10];
                case 9:
                    this.logger.log(l.Debug, "HttpConnection.transport is undefined in HttpConnection.stop() because start() failed."),
                    r.label = 10;
                case 10:
                    return [2]
                }
            })
        })
    }
    ,
    o.prototype.startInternal = function(t) {
        return P(this, void 0, void 0, function() {
            var e, r, i, n, c, a;
            return E(this, function(u) {
                switch (u.label) {
                case 0:
                    e = this.baseUrl,
                    this.accessTokenFactory = this.options.accessTokenFactory,
                    u.label = 1;
                case 1:
                    return u.trys.push([1, 12, , 13]),
                    this.options.skipNegotiation ? this.options.transport !== m.WebSockets ? [3, 3] : (this.transport = this.constructTransport(m.WebSockets),
                    [4, this.startTransport(e, t)]) : [3, 5];
                case 2:
                    return u.sent(),
                    [3, 4];
                case 3:
                    throw new Error("Negotiation can only be skipped when using the WebSocket transport directly.");
                case 4:
                    return [3, 11];
                case 5:
                    r = null,
                    i = 0,
                    n = function() {
                        var s;
                        return E(this, function(h) {
                            switch (h.label) {
                            case 0:
                                return [4, c.getNegotiationResponse(e)];
                            case 1:
                                if (r = h.sent(),
                                c.connectionState === "Disconnecting" || c.connectionState === "Disconnected")
                                    throw new Error("The connection was stopped during negotiation.");
                                if (r.error)
                                    throw new Error(r.error);
                                if (r.ProtocolVersion)
                                    throw new Error("Detected a connection attempt to an ASP.NET SignalR Server. This client only supports connecting to an ASP.NET Core SignalR Server. See https://aka.ms/signalr-core-differences for details.");
                                return r.url && (e = r.url),
                                r.accessToken && (s = r.accessToken,
                                c.accessTokenFactory = function() {
                                    return s
                                }
                                ),
                                i++,
                                [2]
                            }
                        })
                    }
                    ,
                    c = this,
                    u.label = 6;
                case 6:
                    return [5, n()];
                case 7:
                    u.sent(),
                    u.label = 8;
                case 8:
                    if (r.url && i < z)
                        return [3, 6];
                    u.label = 9;
                case 9:
                    if (i === z && r.url)
                        throw new Error("Negotiate redirection limit exceeded.");
                    return [4, this.createTransport(e, this.options.transport, r, t)];
                case 10:
                    u.sent(),
                    u.label = 11;
                case 11:
                    return this.transport instanceof V && (this.features.inherentKeepAlive = !0),
                    this.connectionState === "Connecting" && (this.logger.log(l.Debug, "The HttpConnection connected successfully."),
                    this.connectionState = "Connected"),
                    [3, 13];
                case 12:
                    return a = u.sent(),
                    this.logger.log(l.Error, "Failed to start the connection: " + a),
                    this.connectionState = "Disconnected",
                    this.transport = void 0,
                    this.stopPromiseResolver(),
                    [2, Promise.reject(a)];
                case 13:
                    return [2]
                }
            })
        })
    }
    ,
    o.prototype.getNegotiationResponse = function(t) {
        return P(this, void 0, void 0, function() {
            var e, r, i, n, c, a, u, s, h;
            return E(this, function(f) {
                switch (f.label) {
                case 0:
                    return e = {},
                    this.accessTokenFactory ? [4, this.accessTokenFactory()] : [3, 2];
                case 1:
                    r = f.sent(),
                    r && (e.Authorization = "Bearer " + r),
                    f.label = 2;
                case 2:
                    i = I(),
                    n = i[0],
                    c = i[1],
                    e[n] = c,
                    a = this.resolveNegotiateUrl(t),
                    this.logger.log(l.Debug, "Sending negotiation request: " + a + "."),
                    f.label = 3;
                case 3:
                    return f.trys.push([3, 5, , 6]),
                    [4, this.httpClient.post(a, {
                        content: "",
                        headers: He({}, e, this.options.headers),
                        withCredentials: this.options.withCredentials
                    })];
                case 4:
                    return u = f.sent(),
                    u.statusCode !== 200 ? [2, Promise.reject(new Error("Unexpected status code returned from negotiate '" + u.statusCode + "'"))] : (s = JSON.parse(u.content),
                    (!s.negotiateVersion || s.negotiateVersion < 1) && (s.connectionToken = s.connectionId),
                    [2, s]);
                case 5:
                    return h = f.sent(),
                    this.logger.log(l.Error, "Failed to complete negotiation with the server: " + h),
                    [2, Promise.reject(h)];
                case 6:
                    return [2]
                }
            })
        })
    }
    ,
    o.prototype.createConnectUrl = function(t, e) {
        return e ? t + (t.indexOf("?") === -1 ? "?" : "&") + ("id=" + e) : t
    }
    ,
    o.prototype.createTransport = function(t, e, r, i) {
        return P(this, void 0, void 0, function() {
            var n, c, a, u, s, h, f, d, y, k, v;
            return E(this, function(p) {
                switch (p.label) {
                case 0:
                    return n = this.createConnectUrl(t, r.connectionToken),
                    this.isITransport(e) ? (this.logger.log(l.Debug, "Connection was provided an instance of ITransport, using that directly."),
                    this.transport = e,
                    [4, this.startTransport(n, i)]) : [3, 2];
                case 1:
                    return p.sent(),
                    this.connectionId = r.connectionId,
                    [2];
                case 2:
                    c = [],
                    a = r.availableTransports || [],
                    u = r,
                    s = 0,
                    h = a,
                    p.label = 3;
                case 3:
                    return s < h.length ? (f = h[s],
                    d = this.resolveTransportOrError(f, e, i),
                    d instanceof Error ? (c.push(f.transport + " failed: " + d),
                    [3, 12]) : [3, 4]) : [3, 13];
                case 4:
                    if (!this.isITransport(d))
                        return [3, 12];
                    if (this.transport = d,
                    u)
                        return [3, 9];
                    p.label = 5;
                case 5:
                    return p.trys.push([5, 7, , 8]),
                    [4, this.getNegotiationResponse(t)];
                case 6:
                    return u = p.sent(),
                    [3, 8];
                case 7:
                    return y = p.sent(),
                    [2, Promise.reject(y)];
                case 8:
                    n = this.createConnectUrl(t, u.connectionToken),
                    p.label = 9;
                case 9:
                    return p.trys.push([9, 11, , 12]),
                    [4, this.startTransport(n, i)];
                case 10:
                    return p.sent(),
                    this.connectionId = u.connectionId,
                    [2];
                case 11:
                    return k = p.sent(),
                    this.logger.log(l.Error, "Failed to start the transport '" + f.transport + "': " + k),
                    u = void 0,
                    c.push(f.transport + " failed: " + k),
                    this.connectionState !== "Connecting" ? (v = "Failed to select transport before stop() was called.",
                    this.logger.log(l.Debug, v),
                    [2, Promise.reject(new Error(v))]) : [3, 12];
                case 12:
                    return s++,
                    [3, 3];
                case 13:
                    return c.length > 0 ? [2, Promise.reject(new Error("Unable to connect to the server with any of the available transports. " + c.join(" ")))] : [2, Promise.reject(new Error("None of the transports supported by the client are supported by the server."))]
                }
            })
        })
    }
    ,
    o.prototype.constructTransport = function(t) {
        switch (t) {
        case m.WebSockets:
            if (!this.options.WebSocket)
                throw new Error("'WebSocket' is not supported in your environment.");
            return new Oe(this.httpClient,this.accessTokenFactory,this.logger,this.options.logMessageContent || !1,this.options.WebSocket,this.options.headers || {});
        case m.ServerSentEvents:
            if (!this.options.EventSource)
                throw new Error("'EventSource' is not supported in your environment.");
            return new _e(this.httpClient,this.accessTokenFactory,this.logger,this.options.logMessageContent || !1,this.options.EventSource,this.options.withCredentials,this.options.headers || {});
        case m.LongPolling:
            return new V(this.httpClient,this.accessTokenFactory,this.logger,this.options.logMessageContent || !1,this.options.withCredentials,this.options.headers || {});
        default:
            throw new Error("Unknown transport: " + t + ".")
        }
    }
    ,
    o.prototype.startTransport = function(t, e) {
        var r = this;
        return this.transport.onreceive = this.onreceive,
        this.transport.onclose = function(i) {
            return r.stopConnection(i)
        }
        ,
        this.transport.connect(t, e)
    }
    ,
    o.prototype.resolveTransportOrError = function(t, e, r) {
        var i = m[t.transport];
        if (i == null)
            return this.logger.log(l.Debug, "Skipping transport '" + t.transport + "' because it is not supported by this client."),
            new Error("Skipping transport '" + t.transport + "' because it is not supported by this client.");
        if (Ae(e, i)) {
            var n = t.transferFormats.map(function(c) {
                return S[c]
            });
            if (n.indexOf(r) >= 0) {
                if (i === m.WebSockets && !this.options.WebSocket || i === m.ServerSentEvents && !this.options.EventSource)
                    return this.logger.log(l.Debug, "Skipping transport '" + m[i] + "' because it is not supported in your environment.'"),
                    new Error("'" + m[i] + "' is not supported in your environment.");
                this.logger.log(l.Debug, "Selecting transport '" + m[i] + "'.");
                try {
                    return this.constructTransport(i)
                } catch (c) {
                    return c
                }
            } else
                return this.logger.log(l.Debug, "Skipping transport '" + m[i] + "' because it does not support the requested transfer format '" + S[r] + "'."),
                new Error("'" + m[i] + "' does not support " + S[r] + ".")
        } else
            return this.logger.log(l.Debug, "Skipping transport '" + m[i] + "' because it was disabled by the client."),
            new Error("'" + m[i] + "' is disabled by the client.")
    }
    ,
    o.prototype.isITransport = function(t) {
        return t && typeof t == "object" && "connect"in t
    }
    ,
    o.prototype.stopConnection = function(t) {
        var e = this;
        if (this.logger.log(l.Debug, "HttpConnection.stopConnection(" + t + ") called while in state " + this.connectionState + "."),
        this.transport = void 0,
        t = this.stopError || t,
        this.stopError = void 0,
        this.connectionState === "Disconnected") {
            this.logger.log(l.Debug, "Call to HttpConnection.stopConnection(" + t + ") was ignored because the connection is already in the disconnected state.");
            return
        }
        if (this.connectionState === "Connecting")
            throw this.logger.log(l.Warning, "Call to HttpConnection.stopConnection(" + t + ") was ignored because the connection is still in the connecting state."),
            new Error("HttpConnection.stopConnection(" + t + ") was called while the connection is still in the connecting state.");
        if (this.connectionState === "Disconnecting" && this.stopPromiseResolver(),
        t ? this.logger.log(l.Error, "Connection disconnected with error '" + t + "'.") : this.logger.log(l.Information, "Connection disconnected."),
        this.sendQueue && (this.sendQueue.stop().catch(function(r) {
            e.logger.log(l.Error, "TransportSendQueue.stop() threw error '" + r + "'.")
        }),
        this.sendQueue = void 0),
        this.connectionId = void 0,
        this.connectionState = "Disconnected",
        this.connectionStarted) {
            this.connectionStarted = !1;
            try {
                this.onclose && this.onclose(t)
            } catch (r) {
                this.logger.log(l.Error, "HttpConnection.onclose(" + t + ") threw error '" + r + "'.")
            }
        }
    }
    ,
    o.prototype.resolveUrl = function(t) {
        if (t.lastIndexOf("https://", 0) === 0 || t.lastIndexOf("http://", 0) === 0)
            return t;
        if (!C.isBrowser || !window.document)
            throw new Error("Cannot resolve '" + t + "'.");
        var e = window.document.createElement("a");
        return e.href = t,
        this.logger.log(l.Information, "Normalizing '" + t + "' to '" + e.href + "'."),
        e.href
    }
    ,
    o.prototype.resolveNegotiateUrl = function(t) {
        var e = t.indexOf("?")
          , r = t.substring(0, e === -1 ? t.length : e);
        return r[r.length - 1] !== "/" && (r += "/"),
        r += "negotiate",
        r += e === -1 ? "" : t.substring(e),
        r.indexOf("negotiateVersion") === -1 && (r += e === -1 ? "?" : "&",
        r += "negotiateVersion=" + this.negotiateVersion),
        r
    }
    ,
    o
}
)();
function Ae(o, t) {
    return !o || (t & o) !== 0
}
var We = (function() {
    function o(t) {
        this.transport = t,
        this.buffer = [],
        this.executing = !0,
        this.sendBufferedData = new W,
        this.transportResult = new W,
        this.sendLoopPromise = this.sendLoop()
    }
    return o.prototype.send = function(t) {
        return this.bufferData(t),
        this.transportResult || (this.transportResult = new W),
        this.transportResult.promise
    }
    ,
    o.prototype.stop = function() {
        return this.executing = !1,
        this.sendBufferedData.resolve(),
        this.sendLoopPromise
    }
    ,
    o.prototype.bufferData = function(t) {
        if (this.buffer.length && typeof this.buffer[0] != typeof t)
            throw new Error("Expected data to be of type " + typeof this.buffer + " but was of type " + typeof t);
        this.buffer.push(t),
        this.sendBufferedData.resolve()
    }
    ,
    o.prototype.sendLoop = function() {
        return P(this, void 0, void 0, function() {
            var t, e, r;
            return E(this, function(i) {
                switch (i.label) {
                case 0:
                    return [4, this.sendBufferedData.promise];
                case 1:
                    if (i.sent(),
                    !this.executing)
                        return this.transportResult && this.transportResult.reject("Connection stopped."),
                        [3, 6];
                    this.sendBufferedData = new W,
                    t = this.transportResult,
                    this.transportResult = void 0,
                    e = typeof this.buffer[0] == "string" ? this.buffer.join("") : o.concatBuffers(this.buffer),
                    this.buffer.length = 0,
                    i.label = 2;
                case 2:
                    return i.trys.push([2, 4, , 5]),
                    [4, this.transport.send(e)];
                case 3:
                    return i.sent(),
                    t.resolve(),
                    [3, 5];
                case 4:
                    return r = i.sent(),
                    t.reject(r),
                    [3, 5];
                case 5:
                    return [3, 0];
                case 6:
                    return [2]
                }
            })
        })
    }
    ,
    o.concatBuffers = function(t) {
        for (var e = t.map(function(u) {
            return u.byteLength
        }).reduce(function(u, s) {
            return u + s
        }), r = new Uint8Array(e), i = 0, n = 0, c = t; n < c.length; n++) {
            var a = c[n];
            r.set(new Uint8Array(a), i),
            i += a.byteLength
        }
        return r.buffer
    }
    ,
    o
}
)()
  , W = (function() {
    function o() {
        var t = this;
        this.promise = new Promise(function(e, r) {
            var i;
            return i = [e, r],
            t.resolver = i[0],
            t.rejecter = i[1],
            i
        }
        )
    }
    return o.prototype.resolve = function() {
        this.resolver()
    }
    ,
    o.prototype.reject = function(t) {
        this.rejecter(t)
    }
    ,
    o
}
)()
  , Ne = "json"
  , Ue = (function() {
    function o() {
        this.name = Ne,
        this.version = 1,
        this.transferFormat = S.Text
    }
    return o.prototype.parseMessages = function(t, e) {
        if (typeof t != "string")
            throw new Error("Invalid input for JSON hub protocol. Expected a string.");
        if (!t)
            return [];
        e === null && (e = $.instance);
        for (var r = T.parse(t), i = [], n = 0, c = r; n < c.length; n++) {
            var a = c[n]
              , u = JSON.parse(a);
            if (typeof u.type != "number")
                throw new Error("Invalid payload.");
            switch (u.type) {
            case g.Invocation:
                this.isInvocationMessage(u);
                break;
            case g.StreamItem:
                this.isStreamItemMessage(u);
                break;
            case g.Completion:
                this.isCompletionMessage(u);
                break;
            case g.Ping:
                break;
            case g.Close:
                break;
            default:
                e.log(l.Information, "Unknown message type '" + u.type + "' ignored.");
                continue
            }
            i.push(u)
        }
        return i
    }
    ,
    o.prototype.writeMessage = function(t) {
        return T.write(JSON.stringify(t))
    }
    ,
    o.prototype.isInvocationMessage = function(t) {
        this.assertNotEmptyString(t.target, "Invalid payload for Invocation message."),
        t.invocationId !== void 0 && this.assertNotEmptyString(t.invocationId, "Invalid payload for Invocation message.")
    }
    ,
    o.prototype.isStreamItemMessage = function(t) {
        if (this.assertNotEmptyString(t.invocationId, "Invalid payload for StreamItem message."),
        t.item === void 0)
            throw new Error("Invalid payload for StreamItem message.")
    }
    ,
    o.prototype.isCompletionMessage = function(t) {
        if (t.result && t.error)
            throw new Error("Invalid payload for Completion message.");
        !t.result && t.error && this.assertNotEmptyString(t.error, "Invalid payload for Completion message."),
        this.assertNotEmptyString(t.invocationId, "Invalid payload for Completion message.")
    }
    ,
    o.prototype.assertNotEmptyString = function(t, e) {
        if (typeof t != "string" || t === "")
            throw new Error(e)
    }
    ,
    o
}
)()
  , Q = Object.assign || function(o) {
    for (var t, e = 1, r = arguments.length; e < r; e++) {
        t = arguments[e];
        for (var i in t)
            Object.prototype.hasOwnProperty.call(t, i) && (o[i] = t[i])
    }
    return o
}
  , Me = {
    trace: l.Trace,
    debug: l.Debug,
    info: l.Information,
    information: l.Information,
    warn: l.Warning,
    warning: l.Warning,
    error: l.Error,
    critical: l.Critical,
    none: l.None
};
function Le(o) {
    var t = Me[o.toLowerCase()];
    if (typeof t < "u")
        return t;
    throw new Error("Unknown log level: " + o)
}
var $e = (function() {
    function o() {}
    return o.prototype.configureLogging = function(t) {
        if (w.isRequired(t, "logging"),
        Be(t))
            this.logger = t;
        else if (typeof t == "string") {
            var e = Le(t);
            this.logger = new N(e)
        } else
            this.logger = new N(t);
        return this
    }
    ,
    o.prototype.withUrl = function(t, e) {
        return w.isRequired(t, "url"),
        w.isNotEmpty(t, "url"),
        this.url = t,
        typeof e == "object" ? this.httpConnectionOptions = Q({}, this.httpConnectionOptions, e) : this.httpConnectionOptions = Q({}, this.httpConnectionOptions, {
            transport: e
        }),
        this
    }
    ,
    o.prototype.withHubProtocol = function(t) {
        return w.isRequired(t, "protocol"),
        this.protocol = t,
        this
    }
    ,
    o.prototype.withAutomaticReconnect = function(t) {
        if (this.reconnectPolicy)
            throw new Error("A reconnectPolicy has already been set.");
        return t ? Array.isArray(t) ? this.reconnectPolicy = new X(t) : this.reconnectPolicy = t : this.reconnectPolicy = new X,
        this
    }
    ,
    o.prototype.build = function() {
        var t = this.httpConnectionOptions || {};
        if (t.logger === void 0 && (t.logger = this.logger),
        !this.url)
            throw new Error("The 'HubConnectionBuilder.withUrl' method must be called before building the connection.");
        var e = new je(this.url,t);
        return Ee.create(e, this.logger || $.instance, this.protocol || new Ue, this.reconnectPolicy)
    }
    ,
    o
}
)();
function Be(o) {
    return o.log !== void 0
}
export {$e as H, l as L, b as a};
