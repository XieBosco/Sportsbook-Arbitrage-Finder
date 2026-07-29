import {s as E, k3 as o, bi as s, dK as H, dL as l, bl as y, ab as P, aM as W, bT as Q, aN as O, ew as g, w as v, jt as I, C as u, L as $} from "./main.CBNNqjht.js";
import {a as j, c as F} from "./common-settings-hub-options-factory.CSwrI9Hb.js";
import {M as G, D as h} from "./MessageQueue.-OuTDBhN.js";
import {s as U} from "./signalr-hub-connection.service.CsWj2mbc.js";
import "./HubConnectionBuilder.CBkYTUOq.js";
const D = new Worker(new URL("/assets/worker-BeBaSeH1.js",import.meta.url),{
    type: "module"
});
function B(n) {
    D.postMessage({
        command: "DecodeDanaeHubMessage",
        payload: {
            danaeHubMessage: n
        }
    })
}
function x(n) {
    D.onmessage = n
}
function T() {
    return {
        onActiveLiveOverviewVersionChanged: async i => {
            i && await E.dispatch(o.UPDATE_LIVE_OVERVIEW_VERSION, i),
            E.dispatch(o.SYNC_LIVE_OVERVIEW)
        }
        ,
        onNewLiveOverviewDiffsChanged: i => E.dispatch(o.SET_LIVE_OVERVIEW_DIFF_MESSAGE, i)
    }
}
const J = 500;
class z {
    constructor() {
        this.signalrHubConnection = U,
        this.reconnectionStrategyInitialised = null,
        this.messageQueue = new G,
        this.processQueueInterval = null,
        this.isSoftResetting = null
    }
    #e = {};
    get hubOptions() {
        return this.#e
    }
    set hubOptions(e) {
        this.#e = e
    }
    join() {
        if (this.signalrHubConnection.isConnected()) {
            s(`${j} Joining`),
            this.#s(),
            this.consumeWorkerMessages(),
            this.#t(),
            this.reconnectionStrategyInitialised || this.#r();
            return
        }
        setTimeout( () => this.join(), J)
    }
    async leave() {
        await this.#v(),
        this.#i(),
        this.stopProcessingMessages()
    }
    softReset() {
        this.isSoftResetting = !0,
        this.stopProcessingMessages(),
        this.#u()
    }
    consumeWorkerMessages() {
        x( ({data: e}) => {
            const {messages: i} = e;
            if (i instanceof Error) {
                y(i);
                return
            }
            this.onEnqueueMessages(i)
        }
        )
    }
    onEnqueueMessages(e) {
        this.messageQueue.size + e.length > this.hubOptions.maxQueueSize && (s(`@danaeLiveOverview MaxQueueSize exceeded: ${this.maxQueueSize}. Resetting...`),
        this.softReset());
        for (let i = 0; i < e.length; i++)
            this.messageQueue.enqueue(e[i])
    }
    processMessages() {
        s(`${H}: Starting worker iteration`);
        const {onNewLiveOverviewDiffsChanged: e} = T();
        this.processQueueInterval = setInterval( () => {
            const i = this.messageQueue.dequeue();
            i && e(i)
        }
        )
    }
    stopProcessingMessages() {
        this.#n(),
        this.messageQueue.clear()
    }
    #n() {
        clearInterval(this.processQueueInterval),
        this.processQueueInterval = null
    }
    #s() {
        this.#o(),
        this.#a()
    }
    #i() {
        this.signalrHubConnection.unsubscribe(h.OnActiveLiveOverviewVersion),
        this.signalrHubConnection.unsubscribe(h.NewLiveOverviewDiffs)
    }
    #o() {
        this.signalrHubConnection.subscribe(h.OnActiveLiveOverviewVersion, e => {
            this.isSoftResetting && s("@danaeLiveOverview Soft Reset cleared."),
            this.isSoftResetting = !1,
            T().onActiveLiveOverviewVersionChanged(e)
        }
        )
    }
    #a() {
        this.signalrHubConnection.subscribe(h.NewLiveOverviewDiffs, e => {
            if (this.isSoftResetting) {
                s("@danaeLiveOverview Soft Reset is in progress. Skipping batch...");
                return
            }
            B(e)
        }
        )
    }
    #r() {
        this.reconnectionStrategyInitialised = !0,
        this.signalrHubConnection.connection?.onreconnected( () => {
            s(`${l}: connection reconnected`);
            const e = this.signalrHubConnection.connection.methods ?? {};
            Object.prototype.hasOwnProperty.call(e, h.NewLiveOverviewDiffs.toLowerCase()) && (this.#i(),
            this.softReset(),
            this.join())
        }
        )
    }
    #t() {
        const {language: e, platformType: i, includeVirtuals: a} = this.hubOptions;
        return this.signalrHubConnection.invoke(this.hubOptions.joinLiveOverviewGroupWithOptions, {
            language: e,
            platformType: i,
            includeVirtuals: a
        }).catch(r => {
            s(`${l}: Error while invoking joinLiveOverviewVersion on signalR connection ${r}`),
            this.#t()
        }
        )
    }
    #v() {
        const {language: e, platformType: i, includeVirtuals: a} = this.hubOptions;
        return this.signalrHubConnection.invoke(this.hubOptions.leaveLiveOverviewGroupWithOptions, {
            language: e,
            platformType: i,
            includeVirtuals: a
        }).catch(r => s(`${l}: Error while invoking leaveLiveOverviewVersion on signalR connection ${r}`))
    }
    #u() {
        return this.signalrHubConnection.invoke(this.hubOptions.hubResetLiveOverviewInvokeMethod).catch(e => s(`${l}: Error while invoking getLiveOverviewVersion on signalR connection ${e}`))
    }
}
const c = new z;
function q(n) {
    const {maxQueueSize: e=3e3, hubJoinInvokeMethod: i, hubResetInvokeMethod: a, hubLeaveInvokeMethod: r, includeVirtuals: L} = n;
    return {
        maxQueueSize: e,
        includeVirtuals: L,
        hubJoinLiveOverviewInvokeMethod: i,
        hubResetLiveOverviewInvokeMethod: a,
        hubLeaveLiveOverviewInvokeMethod: r,
        joinLiveOverviewGroupWithOptions: "joinLiveOverviewGroupWithOptions",
        leaveLiveOverviewGroupWithOptions: "leaveLiveOverviewGroupWithOptions"
    }
}
const ie = Object.assign({
    name: "LiveOverviewDanaeSubscriptionsContainer"
}, {
    __name: "LiveOverviewDanaeSubscriptionsContainer",
    props: {
        shouldUpdateContent: {
            type: Boolean,
            default: !1
        }
    },
    setup(n) {
        const e = P()
          , i = n;
        W( () => {
            L(),
            b(!0),
            V(),
            M()
        }
        ),
        Q( () => {
            d(),
            m()
        }
        );
        const a = () => {
            f.value && _(),
            w.value && c.join()
        }
          , r = () => {
            d(),
            c.leave()
        }
        ;
        function L() {
            O.$on(g.RESTART_DANAE_HUB_CONNECTION, a),
            O.$on(g.TERMINATE_DANAE_HUB_CONNECTION, r)
        }
        function m() {
            O.$off(g.RESTART_DANAE_HUB_CONNECTION, a),
            O.$off(g.TERMINATE_DANAE_HUB_CONNECTION, r)
        }
        const R = v( () => e.getters[I.GET_SHOULD_RESET_LIVE_OVERVIEW])
          , p = v( () => e.getters[I.GET_HAS_INITIALIZATION_COMPLETED])
          , C = v( () => e.getters.getIsLiveOverviewDanaeSubscriptionEnabled)
          , A = v( () => e.state.liveOverview.isInitialStateLoaded)
          , N = v( () => e.getters.getIsLiveOverviewDanaePollEnabled)
          , w = v( () => i.shouldUpdateContent && C.value && p.value)
          , f = v( () => i.shouldUpdateContent && N.value && p.value)
          , b = t => e.dispatch(o.SET_LIVE_OVERVIEW_LOADING, t)
          , V = () => e.dispatch(o.INIT_SPORTS_LAYOUT_FROM_DANAE)
          , M = () => e.dispatch(o.FETCH_LATEST_STATE_FROM_DANAE)
          , _ = () => e.dispatch(o.START_LIVE_OVERVIEW_DANAE_LATEST_POLLING)
          , d = () => e.dispatch(o.STOP_LIVE_OVERVIEW_DANAE_LATEST_POLLING)
          , k = v( () => ({
            ...F(e.getters.getDanaeCommonSettings),
            ...q(e.getters.getLiveOverviewDanaeConfig)
        }));
        return u(A, t => {
            t && c.processMessages()
        }
        ),
        u(R, t => {
            t && c.softReset()
        }
        ),
        u(p, t => {
            t && b(!1)
        }
        ),
        u(w, t => {
            t ? c.join() : c.leave()
        }
        ),
        u(f, (t, S) => {
            t && _(),
            !t && S && d()
        }
        ),
        u(k, t => c.hubOptions = t, {
            immediate: !0
        }),
        u( () => Object.keys(e.state.liveOverview.events), t => {
            e.dispatch(o.ADD_EVENT_WAS_LIVE, {
                eventIds: t
            })
        }
        ),
        (t, S) => $(t.$slots, "default")
    }
});
export {ie as default};
