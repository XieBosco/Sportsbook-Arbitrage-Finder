(function() {
    "use strict";
    function rr(u) {
        return u && u.__esModule && Object.prototype.hasOwnProperty.call(u, "default") ? u.default : u
    }
    var V = {}, X = {}, b = {}, G;
    function K() {
        return G || (G = 1,
        b.hashU32 = function(a) {
            return a = a | 0,
            a = a + 2127912214 + (a << 12) | 0,
            a = a ^ -949894596 ^ a >>> 19,
            a = a + 374761393 + (a << 5) | 0,
            a = a + -744332180 ^ a << 9,
            a = a + -42973499 + (a << 3) | 0,
            a ^ -1252372727 ^ a >>> 16 | 0
        }
        ,
        b.readU64 = function(a, i) {
            var v = 0;
            return v |= a[i++] << 0,
            v |= a[i++] << 8,
            v |= a[i++] << 16,
            v |= a[i++] << 24,
            v |= a[i++] << 32,
            v |= a[i++] << 40,
            v |= a[i++] << 48,
            v |= a[i++] << 56,
            v
        }
        ,
        b.readU32 = function(a, i) {
            var v = 0;
            return v |= a[i++] << 0,
            v |= a[i++] << 8,
            v |= a[i++] << 16,
            v |= a[i++] << 24,
            v
        }
        ,
        b.writeU32 = function(a, i, v) {
            a[i++] = v >> 0 & 255,
            a[i++] = v >> 8 & 255,
            a[i++] = v >> 16 & 255,
            a[i++] = v >> 24 & 255
        }
        ,
        b.imul = function(a, i) {
            var v = a >>> 16
              , L = a & 65535
              , C = i >>> 16
              , M = i & 65535;
            return L * M + (v * M + L * C << 16) | 0
        }
        ),
        b
    }
    var Q;
    function er() {
        if (Q)
            return X;
        Q = 1;
        var u = K()
          , a = 2654435761
          , i = 2246822519
          , v = 3266489917
          , L = 668265263
          , C = 374761393;
        function M(n, m) {
            return n = n | 0,
            m = m | 0,
            n >>> (32 - m | 0) | n << m | 0
        }
        function F(n, m, l) {
            return n = n | 0,
            m = m | 0,
            l = l | 0,
            u.imul(n >>> (32 - m | 0) | n << m, l) | 0
        }
        function E(n, m) {
            return n = n | 0,
            m = m | 0,
            n >>> m ^ n | 0
        }
        function A(n, m, l, k, w) {
            return F(u.imul(m, l) + n, k, w)
        }
        function _(n, m, l) {
            return F(n + u.imul(m[l], C), 11, a)
        }
        function D(n, m, l) {
            return A(n, u.readU32(m, l), v, 17, L)
        }
        function T(n, m, l) {
            return [A(n[0], u.readU32(m, l + 0), i, 13, a), A(n[1], u.readU32(m, l + 4), i, 13, a), A(n[2], u.readU32(m, l + 8), i, 13, a), A(n[3], u.readU32(m, l + 12), i, 13, a)]
        }
        function R(n, m, l, k) {
            var w, q;
            if (q = k,
            k >= 16) {
                for (w = [n + a + i, n + i, n, n - a]; k >= 16; )
                    w = T(w, m, l),
                    l += 16,
                    k -= 16;
                w = M(w[0], 1) + M(w[1], 7) + M(w[2], 12) + M(w[3], 18) + q
            } else
                w = n + C + k >>> 0;
            for (; k >= 4; )
                w = D(w, m, l),
                l += 4,
                k -= 4;
            for (; k > 0; )
                w = _(w, m, l),
                l++,
                k--;
            return w = E(u.imul(E(u.imul(E(w, 15), i), 13), v), 16),
            w >>> 0
        }
        return X.hash = R,
        X
    }
    var W;
    function fr() {
        return W || (W = 1,
        (function(u) {
            var a = er()
              , i = K()
              , v = 4
              , L = 13
              , C = 5
              , M = 6
              , F = 65536
              , E = 4
              , A = (1 << E) - 1
              , _ = 4
              , D = (1 << _) - 1
              , T = x(5 << 20)
              , R = cr()
              , n = 407708164
              , m = 4
              , l = 8
              , k = 16
              , w = 64
              , q = 192
              , J = 2147483648
              , Y = 7
              , j = 4
              , Z = 7
              , N = {
                4: 65536,
                5: 262144,
                6: 1048576,
                7: 4194304
            };
            function cr() {
                try {
                    return new Uint32Array(F)
                } catch {
                    for (var U = new Array(F), f = 0; f < F; f++)
                        U[f] = 0;
                    return U
                }
            }
            function lr(U) {
                for (var f = 0; f < F; f++)
                    R[f] = 0
            }
            function x(U) {
                try {
                    return new Uint8Array(U)
                } catch {
                    for (var f = new Array(U), e = 0; e < U; e++)
                        f[e] = 0;
                    return f
                }
            }
            function z(U, f, e) {
                if (typeof U.buffer !== void 0) {
                    if (Uint8Array.prototype.slice)
                        return U.slice(f, e);
                    var r = U.length;
                    f = f | 0,
                    f = f < 0 ? Math.max(r + f, 0) : Math.min(f, r),
                    e = e === void 0 ? r : e | 0,
                    e = e < 0 ? Math.max(r + e, 0) : Math.min(e, r);
                    for (var h = new Uint8Array(e - f), p = f, o = 0; p < e; )
                        h[o++] = U[p++];
                    return h
                } else
                    return U.slice(f, e)
            }
            u.compressBound = function(f) {
                return f + f / 255 + 16 | 0
            }
            ,
            u.decompressBound = function(f) {
                var e = 0;
                if (i.readU32(f, e) !== n)
                    throw new Error("invalid magic number");
                e += 4;
                var r = f[e++];
                if ((r & q) !== w)
                    throw new Error("incompatible descriptor version " + (r & q));
                var h = (r & k) !== 0
                  , p = (r & l) !== 0
                  , o = f[e++] >> j & Z;
                if (N[o] === void 0)
                    throw new Error("invalid block size " + o);
                var t = N[o];
                if (p)
                    return i.readU64(f, e);
                e++;
                for (var c = 0; ; ) {
                    var s = i.readU32(f, e);
                    if (e += 4,
                    s & J ? (s &= ~J,
                    c += s) : c += t,
                    s === 0)
                        return c;
                    h && (e += 4),
                    e += s
                }
            }
            ,
            u.makeBuffer = x,
            u.decompressBlock = function(f, e, r, h, p) {
                var o, t, c, s, g;
                for (c = r + h; r < c; ) {
                    var d = f[r++]
                      , B = d >> 4;
                    if (B > 0) {
                        if (B === 15)
                            for (; B += f[r],
                            f[r++] === 255; )
                                ;
                        for (s = r + B; r < s; )
                            e[p++] = f[r++]
                    }
                    if (r >= c)
                        break;
                    if (o = d & 15,
                    t = f[r++] | f[r++] << 8,
                    o === 15)
                        for (; o += f[r],
                        f[r++] === 255; )
                            ;
                    for (o += v,
                    g = p - t,
                    s = g + o; g < s; )
                        e[p++] = e[g++] | 0
                }
                return p
            }
            ,
            u.compressBlock = function(f, e, r, h, p) {
                var o, t, c, s, g, d, B, O, y;
                if (B = 0,
                O = h + r,
                t = r,
                h >= L)
                    for (var S = (1 << M) + 3; r + v < O - C; ) {
                        var $ = i.readU32(f, r)
                          , H = i.hashU32($) >>> 0;
                        if (H = (H >> 16 ^ H) >>> 0 & 65535,
                        o = p[H] - 1,
                        p[H] = r + 1,
                        o < 0 || r - o >>> 16 > 0 || i.readU32(f, o) !== $) {
                            g = S++ >> M,
                            r += g;
                            continue
                        }
                        for (S = (1 << M) + 3,
                        d = r - t,
                        s = r - o,
                        r += v,
                        o += v,
                        c = r; r < O - C && f[r] === f[o]; )
                            r++,
                            o++;
                        c = r - c;
                        var I = c < A ? c : A;
                        if (d >= D) {
                            for (e[B++] = (D << E) + I,
                            y = d - D; y >= 255; y -= 255)
                                e[B++] = 255;
                            e[B++] = y
                        } else
                            e[B++] = (d << E) + I;
                        for (var P = 0; P < d; P++)
                            e[B++] = f[t + P];
                        if (e[B++] = s,
                        e[B++] = s >> 8,
                        c >= A) {
                            for (y = c - A; y >= 255; y -= 255)
                                e[B++] = 255;
                            e[B++] = y
                        }
                        t = r
                    }
                if (t === 0)
                    return 0;
                if (d = O - t,
                d >= D) {
                    for (e[B++] = D << E,
                    y = d - D; y >= 255; y -= 255)
                        e[B++] = 255;
                    e[B++] = y
                } else
                    e[B++] = d << E;
                for (r = t; r < O; )
                    e[B++] = f[r++];
                return B
            }
            ,
            u.decompressFrame = function(f, e) {
                var r, h, p, o, t = 0, c = 0;
                if (i.readU32(f, t) !== n)
                    throw new Error("invalid magic number");
                if (t += 4,
                o = f[t++],
                (o & q) !== w)
                    throw new Error("incompatible descriptor version");
                r = (o & k) !== 0,
                h = (o & m) !== 0,
                p = (o & l) !== 0;
                var s = f[t++] >> j & Z;
                if (N[s] === void 0)
                    throw new Error("invalid block size");
                for (p && (t += 8),
                t++; ; ) {
                    var g;
                    if (g = i.readU32(f, t),
                    t += 4,
                    g === 0)
                        break;
                    if (r && (t += 4),
                    (g & J) !== 0) {
                        g &= ~J;
                        for (var d = 0; d < g; d++)
                            e[c++] = f[t++]
                    } else
                        c = u.decompressBlock(f, e, t, g, c),
                        t += g
                }
                return h && (t += 4),
                c
            }
            ,
            u.compressFrame = function(f, e) {
                var r = 0;
                i.writeU32(e, r, n),
                r += 4,
                e[r++] = w,
                e[r++] = Y << j,
                e[r] = a.hash(0, e, 4, r - 4) >> 8,
                r++;
                var h = N[Y]
                  , p = f.length
                  , o = 0;
                for (lr(); p > 0; ) {
                    var t = 0
                      , c = p > h ? h : p;
                    if (t = u.compressBlock(f, T, o, c, R),
                    t > c || t === 0) {
                        i.writeU32(e, r, 2147483648 | c),
                        r += 4;
                        for (var s = o + c; o < s; )
                            e[r++] = f[o++];
                        p -= c
                    } else {
                        i.writeU32(e, r, t),
                        r += 4;
                        for (var g = 0; g < t; )
                            e[r++] = T[g++];
                        o += c,
                        p -= c
                    }
                }
                return i.writeU32(e, r, 0),
                r += 4,
                r
            }
            ,
            u.decompress = function(f, e) {
                var r, h;
                return e === void 0 && (e = u.decompressBound(f)),
                r = u.makeBuffer(e),
                h = u.decompressFrame(f, r),
                h !== e && (r = z(r, 0, h)),
                r
            }
            ,
            u.compress = function(f, e) {
                var r, h;
                return e === void 0 && (e = u.compressBound(f.length)),
                r = u.makeBuffer(e),
                h = u.compressFrame(f, r),
                h !== e && (r = z(r, 0, h)),
                r
            }
        }
        )(V)),
        V
    }
    var ar = fr()
      , ur = rr(ar);
    const ir = u => Uint8Array.from(atob(u), a => a.charCodeAt(0))
      , nr = u => ur.decompress(u)
      , or = u => new TextDecoder().decode(u)
      , tr = u => {
        try {
            return JSON.parse(u)
        } catch (a) {
            return a
        }
    }
    ;
    function vr(u) {
        return tr(or(nr(ir(u))))
    }
    self.addEventListener("message", ({data: {command: u, payload: a}}) => {
        if (u === "DecodeDanaeHubMessage") {
            const i = mr(a.danaeHubMessage);
            self.postMessage({
                command: "DanaeHubMessageDecoded",
                messages: i
            })
        }
    }
    );
    function mr(u) {
        return typeof u == "string" ? vr(u) : u
    }
}
)();
