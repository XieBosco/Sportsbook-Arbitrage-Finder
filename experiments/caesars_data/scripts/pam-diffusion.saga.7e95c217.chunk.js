"use strict";
(self.webpackChunkwilliam_hill = self.webpackChunkwilliam_hill || []).push([[9465], {
    76268: function(e, n, t) {
        t.r(n),
        t.d(n, {
            buildPamUpdateEvent: function() {
                return F
            },
            closeSession: function() {
                return z
            },
            default: function() {
                return q
            },
            disconnectDiffusionSession: function() {
                return Z
            },
            handlePamTopicsUpdates: function() {
                return M
            },
            handleWalletUpdate: function() {
                return G
            },
            initializePamDiffusion: function() {
                return _
            },
            startInitializePamDiffusion: function() {
                return X
            },
            subscribeAllPamTopics: function() {
                return j
            },
            subscribedToPamTopicFailure: function() {
                return H
            },
            subscribedToPamTopicSuccess: function() {
                return V
            },
            unsubscribeAllPamTopics: function() {
                return Q
            },
            unsubscribedFromPamTopicFailure: function() {
                return W
            },
            unsubscribedFromPamTopicSuccess: function() {
                return K
            }
        });
        var r = t(4942)
          , s = t(64687)
          , c = t.n(s)
          , a = (t(63497),
        t(82509),
        t(81165),
        t(62809),
        t(75134),
        t(77801),
        t(49740),
        t(24555),
        t(62425),
        t(41658),
        t(17143),
        t(65350),
        t(24637))
          , i = t(59874)
          , u = t(48874)
          , o = t(70258)
          , p = t(49463)
          , f = t(65659)
          , l = t(51315)
          , b = t(61678)
          , d = t(11927)
          , m = t(38384)
          , S = t(50365);
        window.logCzrPamDiffusion = !1;
        var x = {
            SESSION: "Session",
            WALLET: "Wallet",
            KYC: "KYC",
            PAYMENT: "Payment"
        }
          , P = [x.SESSION, x.WALLET, x.KYC, x.PAYMENT]
          , v = function(e, n) {
            var t = m.H.buildUniverse({
                region: e
            });
            return "PAM/v3/".concat(t, "/").concat(n)
        }
          , E = t(76368)
          , w = t(20713)
          , T = t(55766)
          , U = t(49665)
          , I = t(95620);
        function A(e, n) {
            var t = Object.keys(e);
            if (Object.getOwnPropertySymbols) {
                var r = Object.getOwnPropertySymbols(e);
                n && (r = r.filter((function(n) {
                    return Object.getOwnPropertyDescriptor(e, n).enumerable
                }
                ))),
                t.push.apply(t, r)
            }
            return t
        }
        function C(e) {
            for (var n = 1; n < arguments.length; n++) {
                var t = null != arguments[n] ? arguments[n] : {};
                n % 2 ? A(Object(t), !0).forEach((function(n) {
                    (0,
                    r.Z)(e, n, t[n])
                }
                )) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : A(Object(t)).forEach((function(n) {
                    Object.defineProperty(e, n, Object.getOwnPropertyDescriptor(t, n))
                }
                ))
            }
            return e
        }
        var O, h, k = c().mark(_), N = c().mark(j), B = c().mark(z), D = c().mark(Q), Y = c().mark(Z), g = c().mark(X), y = c().mark(G), L = c().mark(q), R = (O = "pam-diffusion.saga",
        function(e) {
            if ((0,
            S.gH)() && window.logCzrPamDiffusion) {
                for (var n, t = arguments.length, r = new Array(t > 1 ? t - 1 : 0), s = 1; s < t; s++)
                    r[s - 1] = arguments[s];
                (n = console).debug.apply(n, ["[CZR_PAM_DIFFUSION:".concat(O, "]: ").concat(e)].concat(r))
            }
        }
        ), F = function(e, n) {
            return {
                actionType: w.KIF.PUSH_UPDATE,
                payload: {
                    topic: e,
                    message: n.get()
                }
            }
        };
        function _() {
            var e, n, t, r, s, i, u, o;
            return c().wrap((function(c) {
                for (; ; )
                    switch (c.prev = c.next) {
                    case 0:
                        return c.next = 2,
                        (0,
                        a.Ys)(f.VS);
                    case 2:
                        return e = c.sent,
                        c.next = 5,
                        (0,
                        a.Ys)(f.mm);
                    case 5:
                        return n = c.sent,
                        c.next = 8,
                        (0,
                        a.Ys)(l.NQ);
                    case 8:
                        return t = c.sent,
                        r = m.H.buildUniverse({
                            region: n
                        }),
                        s = "".concat(r, "/").concat(t),
                        c.next = 13,
                        (0,
                        a.Ys)(l.Jv);
                    case 13:
                        return i = c.sent,
                        c.next = 16,
                        (0,
                        a.Ys)(f.iv);
                    case 16:
                        return u = c.sent,
                        o = "".concat(e.split("/")[0], "/pam"),
                        R("initialPamDiffusion()", {
                            diffusionAddr: e,
                            apiRegionCode: u,
                            playerId: t,
                            pamDiffusionAddress: o,
                            diffusionPrincipal: s,
                            sessionToken: i
                        }),
                        h = Date.now(),
                        c.next = 22,
                        (0,
                        a.RE)(p.ZP, w.Pte, o, d.dL, (0,
                        p.Kt)(F), T.Vr.CONNECTION, !0, s, i);
                    case 22:
                    case "end":
                        return c.stop()
                    }
            }
            ), k)
        }
        function j() {
            var e, n, t, r, s, i, p, m;
            return c().wrap((function(c) {
                for (; ; )
                    switch (c.prev = c.next) {
                    case 0:
                        return c.next = 2,
                        (0,
                        a.Ys)(b.mdV);
                    case 2:
                        return e = c.sent,
                        c.next = 5,
                        (0,
                        a.Ys)(l.b2);
                    case 5:
                        if (n = c.sent,
                        t = (0,
                        d.ay)(),
                        R("subscribeAllPamTopics()", {
                            useBopPam: e,
                            isSessionAuthenticated: n,
                            socketSession: t
                        }),
                        t && n) {
                            c.next = 10;
                            break
                        }
                        return c.abrupt("return");
                    case 10:
                        if (!e) {
                            c.next = 32;
                            break
                        }
                        return c.prev = 11,
                        c.next = 14,
                        (0,
                        a.Ys)(f.mm);
                    case 14:
                        return r = c.sent,
                        c.next = 17,
                        (0,
                        a.Ys)(l.NQ);
                    case 17:
                        return s = c.sent,
                        i = v(r, s),
                        p = P.map((function(e) {
                            return "".concat(i, "/").concat(e)
                        }
                        )),
                        c.next = 22,
                        (0,
                        a.Ys)(f.iv);
                    case 22:
                        return m = c.sent,
                        R("subscribeAllPamTopics()", {
                            apiRegionCode: m,
                            playerId: s,
                            prefix: i,
                            topics: p
                        }),
                        c.next = 26,
                        (0,
                        a.RE)(o.Lj, t, V, H, p);
                    case 26:
                        (0,
                        u.fg)("PAM_DIFFUSION_TOPICS_SUBSCRIBED", {
                            whContext: T.Vr.SUBSCRIBE,
                            totalTime: Date.now() - h
                        }),
                        c.next = 32;
                        break;
                    case 29:
                        c.prev = 29,
                        c.t0 = c.catch(11),
                        (0,
                        u.Nd)(c.t0, {
                            whContext: T.Vr.SUBSCRIBE
                        });
                    case 32:
                    case "end":
                        return c.stop()
                    }
            }
            ), N, null, [[11, 29]])
        }
        function z() {
            return c().wrap((function(e) {
                for (; ; )
                    switch (e.prev = e.next) {
                    case 0:
                        return R("closeSession()"),
                        e.next = 3,
                        (0,
                        a.RE)(Q);
                    case 3:
                        return e.next = 5,
                        (0,
                        a.RE)(Z);
                    case 5:
                    case "end":
                        return e.stop()
                    }
            }
            ), B)
        }
        function Q() {
            var e, n, t;
            return c().wrap((function(r) {
                for (; ; )
                    switch (r.prev = r.next) {
                    case 0:
                        return r.next = 2,
                        (0,
                        a.Ys)(b.mdV);
                    case 2:
                        if (e = r.sent,
                        R("unsubscribeAllPamTopics()", {
                            useBopPam: e
                        }),
                        !e) {
                            r.next = 18;
                            break
                        }
                        return r.prev = 5,
                        n = (0,
                        d.ay)(),
                        r.next = 9,
                        (0,
                        a.Ys)(E.l6);
                    case 9:
                        return t = r.sent,
                        R("unsubscribeAllPamTopics()", {
                            unsubscribeAllPamTopics: Q
                        }),
                        r.next = 13,
                        (0,
                        a.RE)(o.Br, n, K, W, t);
                    case 13:
                        r.next = 18;
                        break;
                    case 15:
                        r.prev = 15,
                        r.t0 = r.catch(5),
                        (0,
                        u.Nd)(r.t0, {
                            whContext: T.Vr.UNSUBSCRIBE
                        });
                    case 18:
                    case "end":
                        return r.stop()
                    }
            }
            ), D, null, [[5, 15]])
        }
        function Z() {
            var e, n;
            return c().wrap((function(t) {
                for (; ; )
                    switch (t.prev = t.next) {
                    case 0:
                        return t.next = 2,
                        (0,
                        a.Ys)(b.mdV);
                    case 2:
                        if (e = t.sent,
                        h = null,
                        R("disconnectDiffusionSession()", {
                            useBopPam: e
                        }),
                        !e) {
                            t.next = 15;
                            break
                        }
                        return t.prev = 6,
                        n = (0,
                        d.ay)(),
                        t.next = 10,
                        (0,
                        a.RE)([n, n.close]);
                    case 10:
                        t.next = 15;
                        break;
                    case 12:
                        t.prev = 12,
                        t.t0 = t.catch(6),
                        (0,
                        u.Nd)(t.t0, {
                            whContext: T.Vr.CLOSE
                        });
                    case 15:
                    case "end":
                        return t.stop()
                    }
            }
            ), Y, null, [[6, 12]])
        }
        var V = function(e) {
            return (0,
            i.Z)(w.mQz.SUBSCRIBE_SUCCESS_PUSH)(e)
        }
          , H = function(e, n) {
            return (0,
            i.Z)(w.mQz.SUBSCRIBE_FAILURE_PUSH)({
                topic: e,
                error: n
            })
        }
          , K = function(e) {
            return (0,
            i.Z)(w.mQz.UNSUBSCRIBE_SUCCESS_PUSH)(e)
        }
          , W = function(e, n) {
            return (0,
            i.Z)(w.mQz.UNSUBSCRIBE_FAILURE_PUSH)({
                topics: e,
                error: n
            })
        };
        function M(e) {
            var n = e.payload;
            return c().mark((function e(t) {
                var r;
                return c().wrap((function(e) {
                    for (; ; )
                        switch (e.prev = e.next) {
                        case 0:
                            if (r = null === n || void 0 === n || null === (t = n.topic) || void 0 === t ? void 0 : t.split("/").pop(),
                            R("handlePamTopicsUpdates()", {
                                topicName: r
                            }),
                            !r) {
                                e.next = 19;
                                break
                            }
                            e.t0 = r,
                            e.next = e.t0 === x.SESSION ? 6 : e.t0 === x.WALLET ? 9 : e.t0 === x.KYC ? 12 : e.t0 === x.PAYMENT ? 16 : 19;
                            break;
                        case 6:
                            return e.next = 8,
                            (0,
                            a.gz)((0,
                            i.Z)(w.QX6.SESSION)(n));
                        case 8:
                        case 11:
                        case 15:
                        case 18:
                            return e.abrupt("break", 19);
                        case 9:
                            return e.next = 11,
                            (0,
                            a.gz)((0,
                            i.Z)(w.QX6.WALLET)(n));
                        case 12:
                            return (0,
                            I.trackPlayerVerification)(C({
                                type: w.QX6.KYC
                            }, n)),
                            e.next = 15,
                            (0,
                            a.gz)((0,
                            i.Z)(w.QX6.KYC)(n));
                        case 16:
                            return e.next = 18,
                            (0,
                            a.gz)((0,
                            i.Z)(w.QX6.PAYMENT)(n));
                        case 19:
                        case "end":
                            return e.stop()
                        }
                }
                ), e)
            }
            ))()
        }
        function X() {
            var e, n;
            return c().wrap((function(t) {
                for (; ; )
                    switch (t.prev = t.next) {
                    case 0:
                        return t.next = 2,
                        (0,
                        a.Ys)(l.Wu);
                    case 2:
                        if (null !== (n = t.sent) && void 0 !== n && null !== (e = n.user) && void 0 !== e && e.SessionToken) {
                            t.next = 5;
                            break
                        }
                        return t.abrupt("return");
                    case 5:
                        return t.next = 7,
                        (0,
                        a.Ys)(b.mdV);
                    case 7:
                        if (!t.sent) {
                            t.next = 11;
                            break
                        }
                        return t.next = 11,
                        (0,
                        a.S3)([(0,
                        a.RE)(_), (0,
                        a.qn)(w.FDB.LOGOUT)]);
                    case 11:
                        return t.abrupt("return");
                    case 12:
                    case "end":
                        return t.stop()
                    }
            }
            ), g)
        }
        function G() {
            return c().wrap((function(e) {
                for (; ; )
                    switch (e.prev = e.next) {
                    case 0:
                        return R("handleWalletUpdate()"),
                        e.next = 3,
                        (0,
                        a.RE)(U.r0);
                    case 3:
                    case "end":
                        return e.stop()
                    }
            }
            ), y)
        }
        function q() {
            return c().wrap((function(e) {
                for (; ; )
                    switch (e.prev = e.next) {
                    case 0:
                        return e.next = 2,
                        (0,
                        a.$6)([(0,
                        a.Fm)(w.FDB.LOGIN, X), (0,
                        a.Fm)(w.KIF.MANUAL_INITIALIZATION, X), (0,
                        a.ib)(w.Pte.ESTABLISHED, j), (0,
                        a.ib)(w.FDB.FAILED, Q), (0,
                        a.ib)(w.FDB.LOGOUT, z), (0,
                        a.ib)(w.KIF.PUSH_UPDATE, M), (0,
                        a.ib)(w.QX6.WALLET, G)]);
                    case 2:
                    case "end":
                        return e.stop()
                    }
            }
            ), L)
        }
    }
}]);
//# sourceMappingURL=pam-diffusion.saga.7e95c217.chunk.js.map
