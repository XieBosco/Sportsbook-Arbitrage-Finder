import {ab as I, et as v, eu as O, w as t, ev as B, aM as A, bT as D, aN as o, ew as s, ex as S, C, G as h, K as H} from "./main.CBNNqjht.js";
import {c as g} from "./common-settings-hub-options-factory.CSwrI9Hb.js";
import {s as e} from "./signalr-hub-connection.service.CsWj2mbc.js";
import "./HubConnectionBuilder.CBkYTUOq.js";
const V = Object.assign({
    name: "DanaeHubConnectionContainer"
}, {
    __name: "DanaeHubConnectionContainer",
    props: {
        shouldUpdateContent: {
            type: Boolean,
            default: !1
        }
    },
    setup(E) {
        const m = E
          , c = I()
          , r = v()
          , N = O()
          , _ = t( () => N.value === B.VISIBLE)
          , d = t( () => c.getters.getIsDanaeHubEnabled)
          , a = t( () => d.value && m.shouldUpdateContent && _.value)
          , f = t( () => g(c.getters.getDanaeCommonSettings));
        A( () => {
            p()
        }
        ),
        D( () => {
            i(),
            T()
        }
        );
        function p() {
            o.$on(s.RESTART_DANAE_HUB_CONNECTION, l),
            o.$on(s.TERMINATE_DANAE_HUB_CONNECTION, i)
        }
        function T() {
            o.$off(s.RESTART_DANAE_HUB_CONNECTION, l),
            o.$off(s.TERMINATE_DANAE_HUB_CONNECTION, i)
        }
        const b = () => {
            !e.isConnected() && a.value && e.start()
        }
          , u = () => {
            !e.isConnected() && a.value && e.connect()
        }
          , l = () => {
            r.value ? u() : S(r, n => {
                n && window.location.reload()
            }
            )
        }
          , i = () => e.terminate();
        return C(f, n => e.hubOptions = n, {
            immediate: !0
        }),
        C(a, n => {
            n && (e.connection ? u() : b())
        }
        , {
            immediate: !0
        }),
        (n, w) => (h(),
        H("div"))
    }
});
export {V as default};
