import {D as g, l as u} from "./common-settings-hub-options-factory.CSwrI9Hb.js";
import {bi as e, dK as d, dL as i, dM as b} from "./main.CBNNqjht.js";
import {L as p, H as f, a as m} from "./HubConnectionBuilder.CBkYTUOq.js";
const v = p.Information;
class $ {
    connection;
    #n = {};
    reconnectionTriggered;
    get hubOptions() {
        return this.#n
    }
    set hubOptions(n) {
        this.#n = n
    }
    start() {
        this.#t(this.hubOptions),
        this.connect()
    }
    #t({signalrUrl: n, hubTransportType: t, hubSkipNegotiation: o, serverTimeoutMillis: s, keepAliveIntervalMillis: r, hubHeaders: c={}}, a=v) {
        e(`${g} Building`);
        const l = new Array(5).fill(0).fill(this.hubOptions.hubReconnectIntervalMillis, 1)
          , h = {
            transport: t,
            skipNegotiation: o,
            ...c && {
                headers: c
            }
        };
        this.connection = new f().withUrl(n, h).withAutomaticReconnect(l).configureLogging(a).build(),
        this.connection.serverTimeoutInMilliseconds = s,
        this.connection.keepAliveIntervalInMilliseconds = r,
        this.#i()
    }
    connect() {
        return e(`${d}: Connecting to Danae`),
        u(this.hubOptions?.platformType, "signalR connect", {
            signalrUrl: this.hubOptions?.signalrUrl
        }),
        this.connection.start().catch(n => this.#e(n, this.hubOptions.hubReconnectIntervalMillis))
    }
    #e(n, t) {
        e(`${i}: ReConnect to Danae`, n),
        setTimeout( () => this.connect(), t)
    }
    terminate() {
        if (Object.keys(this.connection.methods ?? {})?.length) {
            setTimeout( () => this.terminate(), 100);
            return
        }
        return e(`${i}: user terminating connection`),
        this.connection.stop().then( () => {
            e(`${i}: terminated connection successfully`)
        }
        ).catch(function(n) {
            b(`${i}: Error while user terminating connection ${n}`)
        })
    }
    subscribe(n, t) {
        this.connection.on(n, t)
    }
    unsubscribe(n, t) {
        this.connection.off(n, t)
    }
    invoke(n, ...t) {
        return this.connection.invoke(n, ...t).catch(o => {
            e(`${i}: Error while invoking ${n} on signalR connection ${o}`)
        }
        )
    }
    #i() {
        this.connection.onclose( () => {
            this.reconnectionTriggered && window.location.reload(),
            e(`${i}: connection closed`)
        }
        ),
        this.connection.onreconnecting( () => {
            this.reconnectionTriggered = !0,
            e(`${i}: connection reconnecting`)
        }
        ),
        this.connection.onreconnected( () => {
            this.reconnectionTriggered = null,
            e(`${i}: connection reconnected`)
        }
        )
    }
    isConnected() {
        return this.connection?.state === m.Connected
    }
}
const T = new $;
export {T as s};
