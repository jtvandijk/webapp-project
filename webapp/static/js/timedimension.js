/*
 * Leaflet TimeDimension v1.1.0 - 2017-10-13
 *
 * Copyright 2017 Biel Frontera (ICTS SOCIB)
 * datacenter@socib.es
 * http://www.socib.es/
 *
 * Licensed under the MIT license.
 *
 * Demos:
 * http://apps.socib.es/Leaflet.TimeDimension/
 *
 * Source:
 * git://github.com/socib/Leaflet.TimeDimension.git
 *
 */
L.TimeDimension = (L.Layer || L.Class).extend({
    includes: L.Evented || L.Mixin.Events,
    initialize: function(a) {
        L.setOptions(this, a),
        this._availableTimes = this._generateAvailableTimes(),
        this._currentTimeIndex = -1,
        this._loadingTimeIndex = -1,
        this._loadingTimeout = this.options.loadingTimeout || 3e3,
        this._syncedLayers = [],
        this._availableTimes.length > 0 && this.setCurrentTime(this.options.currentTime || this._getDefaultCurrentTime()),
        this.options.lowerLimitTime && this.setLowerLimit(this.options.lowerLimitTime),
        this.options.upperLimitTime && this.setUpperLimit(this.options.upperLimitTime)
    },
    getAvailableTimes: function() {
        return this._availableTimes
    },
    getCurrentTimeIndex: function() {
        return -1 === this._currentTimeIndex ? this._availableTimes.length - 1 : this._currentTimeIndex
    },
    getCurrentTime: function() {
        var a = -1;
        return a = -1 !== this._loadingTimeIndex ? this._loadingTimeIndex : this.getCurrentTimeIndex(),
        a >= 0 ? this._availableTimes[a] : null
    },
    isLoading: function() {
        return -1 !== this._loadingTimeIndex
    },
    setCurrentTimeIndex: function(a) {
        var b = this._upperLimit || this._availableTimes.length - 1
          , c = this._lowerLimit || 0;
        if (a = Math.min(Math.max(c, a), b),
        !(0 > a)) {
            this._loadingTimeIndex = a;
            var d = this._availableTimes[a];
            this._checkSyncedLayersReady(this._availableTimes[this._loadingTimeIndex]) ? this._newTimeIndexLoaded() : (this.fire("timeloading", {
                time: d
            }),
            setTimeout(function(a) {
                a == this._loadingTimeIndex && this._newTimeIndexLoaded()
            }
            .bind(this, a), this._loadingTimeout))
        }
    },
    _newTimeIndexLoaded: function() {
        if (-1 !== this._loadingTimeIndex) {
            var a = this._availableTimes[this._loadingTimeIndex];
            this._currentTimeIndex = this._loadingTimeIndex,
            this.fire("timeload", {
                time: a
            }),
            this._loadingTimeIndex = -1
        }
    },
    _checkSyncedLayersReady: function(a) {
        for (var b = 0, c = this._syncedLayers.length; c > b; b++)
            if (this._syncedLayers[b].isReady && !this._syncedLayers[b].isReady(a))
                return !1;
        return !0
    },
    setCurrentTime: function(a) {
        var b = this._seekNearestTimeIndex(a);
        this.setCurrentTimeIndex(b)
    },
    seekNearestTime: function(a) {
        var b = this._seekNearestTimeIndex(a);
        return this._availableTimes[b]
    },
    nextTime: function(a, b) {
        a || (a = 1);
        var c = this._currentTimeIndex
          , d = this._upperLimit || this._availableTimes.length - 1
          , e = this._lowerLimit || 0;
        this._loadingTimeIndex > -1 && (c = this._loadingTimeIndex),
        c += a,
        c > d && (c = b ? e : d),
        e > c && (c = b ? d : e),
        this.setCurrentTimeIndex(c)
    },
    prepareNextTimes: function(a, b, c) {
        a || (a = 1);
        var d = this._currentTimeIndex
          , e = d;
        this._loadingTimeIndex > -1 && (d = this._loadingTimeIndex);
        for (var f = 0, g = this._syncedLayers.length; g > f; f++)
            this._syncedLayers[f].setMinimumForwardCache && this._syncedLayers[f].setMinimumForwardCache(b);
        for (var h = b, i = this._upperLimit || this._availableTimes.length - 1, j = this._lowerLimit || 0; h > 0; ) {
            if (d += a,
            d > i) {
                if (!c)
                    break;
                d = j
            }
            if (j > d) {
                if (!c)
                    break;
                d = i
            }
            if (e === d)
                break;
            this.fire("timeloading", {
                time: this._availableTimes[d]
            }),
            h--
        }
    },
    getNumberNextTimesReady: function(a, b, c) {
        a || (a = 1);
        var d = this._currentTimeIndex;
        this._loadingTimeIndex > -1 && (d = this._loadingTimeIndex);
        for (var e = b, f = 0, g = this._upperLimit || this._availableTimes.length - 1, h = this._lowerLimit || 0; e > 0; ) {
            if (d += a,
            d > g) {
                if (!c) {
                    e = 0,
                    f = b;
                    break
                }
                d = h
            }
            if (h > d) {
                if (!c) {
                    e = 0,
                    f = b;
                    break
                }
                d = g
            }
            var i = this._availableTimes[d];
            this._checkSyncedLayersReady(i) && f++,
            e--
        }
        return f
    },
    previousTime: function(a, b) {
        this.nextTime(-1 * a, b)
    },
    registerSyncedLayer: function(a) {
        this._syncedLayers.push(a),
        a.on("timeload", this._onSyncedLayerLoaded, this)
    },
    unregisterSyncedLayer: function(a) {
        var b = this._syncedLayers.indexOf(a);
        -1 != b && this._syncedLayers.splice(b, 1),
        a.off("timeload", this._onSyncedLayerLoaded, this)
    },
    _onSyncedLayerLoaded: function(a) {
        a.time == this._availableTimes[this._loadingTimeIndex] && this._checkSyncedLayersReady(a.time) && this._newTimeIndexLoaded()
    },
    _generateAvailableTimes: function() {
        if (this.options.times)
            return L.TimeDimension.Util.parseTimesExpression(this.options.times);
        if (this.options.timeInterval) {
            var a = L.TimeDimension.Util.parseTimeInterval(this.options.timeInterval)
              , b = this.options.period || "P1D"
              , c = this.options.validTimeRange || void 0;
            return L.TimeDimension.Util.explodeTimeRange(a[0], a[1], b, c)
        }
        return []
    },
    _getDefaultCurrentTime: function() {
        var a = this._seekNearestTimeIndex((new Date).getTime());
        return this._availableTimes[a]
    },
    _seekNearestTimeIndex: function(a) {
        for (var b = 0, c = this._availableTimes.length; c > b && !(a < this._availableTimes[b]); b++)
            ;
        return b > 0 && b--,
        b
    },
    setAvailableTimes: function(a, b) {
        var c = this.getCurrentTime()
          , d = this.getLowerLimit()
          , e = this.getUpperLimit();
        if ("extremes" == b) {
            var f = this.options.period || "P1D";
            this._availableTimes = L.TimeDimension.Util.explodeTimeRange(new Date(a[0]), new Date(a[a.length - 1]), f)
        } else {
            var g = L.TimeDimension.Util.parseTimesExpression(a);
            if (0 === this._availableTimes.length)
                this._availableTimes = g;
            else if ("intersect" == b)
                this._availableTimes = L.TimeDimension.Util.intersect_arrays(g, this._availableTimes);
            else if ("union" == b)
                this._availableTimes = L.TimeDimension.Util.union_arrays(g, this._availableTimes);
            else {
                if ("replace" != b)
                    throw "Merge available times mode not implemented: " + b;
                this._availableTimes = g
            }
        }
        d && this.setLowerLimit(d),
        e && this.setUpperLimit(e),
        this.setCurrentTime(c),
        this.fire("availabletimeschanged", {
            availableTimes: this._availableTimes,
            currentTime: c
        })
    },
    getLowerLimit: function() {
        return this._availableTimes[this.getLowerLimitIndex()]
    },
    getUpperLimit: function() {
        return this._availableTimes[this.getUpperLimitIndex()]
    },
    setLowerLimit: function(a) {
        var b = this._seekNearestTimeIndex(a);
        this.setLowerLimitIndex(b)
    },
    setUpperLimit: function(a) {
        var b = this._seekNearestTimeIndex(a);
        this.setUpperLimitIndex(b)
    },
    setLowerLimitIndex: function(a) {
        this._lowerLimit = Math.min(Math.max(a || 0, 0), this._upperLimit || this._availableTimes.length - 1),
        this.fire("limitschanged", {
            lowerLimit: this._lowerLimit,
            upperLimit: this._upperLimit
        })
    },
    setUpperLimitIndex: function(a) {
        this._upperLimit = Math.max(Math.min(a, this._availableTimes.length - 1), this._lowerLimit || 0),
        this.fire("limitschanged", {
            lowerLimit: this._lowerLimit,
            upperLimit: this._upperLimit
        })
    },
    getLowerLimitIndex: function() {
        return this._lowerLimit
    },
    getUpperLimitIndex: function() {
        return this._upperLimit
    }
}),
L.Map.addInitHook(function() {
    this.options.timeDimension && (this.timeDimension = L.timeDimension(this.options.timeDimensionOptions || {}))
}),
L.timeDimension = function(a) {
    return new L.TimeDimension(a)
}
,
L.TimeDimension.Util = {
    getTimeDuration: function(a) {
        if ("undefined" == typeof nezasa)
            throw "iso8601-js-period library is required for Leatlet.TimeDimension: https://github.com/nezasa/iso8601-js-period";
        return nezasa.iso8601.Period.parse(a, !0)
    },
    addTimeDuration: function(a, b, c) {
        "undefined" == typeof c && (c = !0),
        ("string" == typeof b || b instanceof String) && (b = this.getTimeDuration(b));
        var d = b.length
          , e = c ? "getUTC" : "get"
          , f = c ? "setUTC" : "set";
        d > 0 && 0 != b[0] && a[f + "FullYear"](a[e + "FullYear"]() + b[0]),
        d > 1 && 0 != b[1] && a[f + "Month"](a[e + "Month"]() + b[1]),
        d > 2 && 0 != b[2] && a[f + "Date"](a[e + "Date"]() + 7 * b[2]),
        d > 3 && 0 != b[3] && a[f + "Date"](a[e + "Date"]() + b[3]),
        d > 4 && 0 != b[4] && a[f + "Hours"](a[e + "Hours"]() + b[4]),
        d > 5 && 0 != b[5] && a[f + "Minutes"](a[e + "Minutes"]() + b[5]),
        d > 6 && 0 != b[6] && a[f + "Seconds"](a[e + "Seconds"]() + b[6])
    },
    subtractTimeDuration: function(a, b, c) {
        ("string" == typeof b || b instanceof String) && (b = this.getTimeDuration(b));
        for (var d = [], e = 0, f = b.length; f > e; e++)
            d.push(-b[e]);
        this.addTimeDuration(a, d, c)
    },
    parseAndExplodeTimeRange: function(a) {
        var b = a.split("/")
          , c = new Date(Date.parse(b[0]))
          , d = new Date(Date.parse(b[1]))
          , e = b.length > 2 ? b[2] : "P1D";
        return this.explodeTimeRange(c, d, e)
    },
    explodeTimeRange: function(a, b, c, d) {
        var e = this.getTimeDuration(c)
          , f = []
          , g = new Date(a.getTime())
          , h = null
          , i = null
          , j = null
          , k = null;
        if (void 0 !== d) {
            var l = d.split("/");
            h = l[0].split(":")[0],
            i = l[0].split(":")[1],
            j = l[1].split(":")[0],
            k = l[1].split(":")[1]
        }
        for (; b > g; )
            (void 0 === d || g.getUTCHours() >= h && g.getUTCHours() <= j) && (g.getUTCHours() != h || g.getUTCMinutes() >= i) && (g.getUTCHours() != j || g.getUTCMinutes() <= k) && f.push(g.getTime()),
            this.addTimeDuration(g, e);
        return g >= b && f.push(b.getTime()),
        f
    },
    parseTimeInterval: function(a) {
        var b = a.split("/");
        if (2 != b.length)
            throw "Incorrect ISO9601 TimeInterval: " + a;
        var c = Date.parse(b[0])
          , d = null
          , e = null;
        return isNaN(c) ? (e = this.getTimeDuration(b[0]),
        d = Date.parse(b[1]),
        c = new Date(d),
        this.subtractTimeDuration(c, e, !0),
        d = new Date(d)) : (d = Date.parse(b[1]),
        isNaN(d) ? (e = this.getTimeDuration(b[1]),
        d = new Date(c),
        this.addTimeDuration(d, e, !0)) : d = new Date(d),
        c = new Date(c)),
        [c, d]
    },
    parseTimesExpression: function(a) {
        var b = [];
        if (!a)
            return b;
        if ("string" == typeof a || a instanceof String)
            for (var c, d, e = a.split(","), f = 0, g = e.length; g > f; f++)
                c = e[f],
                3 == c.split("/").length ? b = b.concat(this.parseAndExplodeTimeRange(c)) : (d = Date.parse(c),
                isNaN(d) || b.push(d));
        else
            b = a;
        return b.sort(function(a, b) {
            return a - b
        })
    },
    intersect_arrays: function(a, b) {
        for (var c = a.slice(0), d = b.slice(0), e = []; c.length > 0 && d.length > 0; )
            c[0] < d[0] ? c.shift() : c[0] > d[0] ? d.shift() : (e.push(c.shift()),
            d.shift());
        return e
    },
    union_arrays: function(a, b) {
        for (var c = a.slice(0), d = b.slice(0), e = []; c.length > 0 && d.length > 0; )
            c[0] < d[0] ? e.push(c.shift()) : c[0] > d[0] ? e.push(d.shift()) : (e.push(c.shift()),
            d.shift());
        return c.length > 0 ? e = e.concat(c) : d.length > 0 && (e = e.concat(d)),
        e
    }
},
L.TimeDimension.Layer = (L.Layer || L.Class).extend({
    includes: L.Evented || L.Mixin.Events,
    options: {
        opacity: 1,
        zIndex: 1
    },
    initialize: function(a, b) {
        L.setOptions(this, b || {}),
        this._map = null,
        this._baseLayer = a,
        this._currentLayer = null,
        this._timeDimension = this.options.timeDimension || null
    },
    addTo: function(a) {
        return a.addLayer(this),
        this
    },
    onAdd: function(a) {
        this._map = a,
        !this._timeDimension && a.timeDimension && (this._timeDimension = a.timeDimension),
        this._timeDimension.on("timeloading", this._onNewTimeLoading, this),
        this._timeDimension.on("timeload", this._update, this),
        this._timeDimension.registerSyncedLayer(this),
        this._update()
    },
    onRemove: function(a) {
        this._timeDimension.unregisterSyncedLayer(this),
        this._timeDimension.off("timeloading", this._onNewTimeLoading, this),
        this._timeDimension.off("timeload", this._update, this),
        this.eachLayer(a.removeLayer, a),
        this._map = null
    },
    eachLayer: function(a, b) {
        return a.call(b, this._baseLayer),
        this
    },
    setZIndex: function(a) {
        return this.options.zIndex = a,
        this._baseLayer.setZIndex && this._baseLayer.setZIndex(a),
        this._currentLayer && this._currentLayer.setZIndex && this._currentLayer.setZIndex(a),
        this
    },
    setOpacity: function(a) {
        return this.options.opacity = a,
        this._baseLayer.setOpacity && this._baseLayer.setOpacity(a),
        this._currentLayer && this._currentLayer.setOpacity && this._currentLayer.setOpacity(a),
        this
    },
    bringToBack: function() {
        return this._currentLayer ? (this._currentLayer.bringToBack(),
        this) : void 0
    },
    bringToFront: function() {
        return this._currentLayer ? (this._currentLayer.bringToFront(),
        this) : void 0
    },
    _onNewTimeLoading: function(a) {
        this.fire("timeload", {
            time: a.time
        })
    },
    isReady: function(a) {
        return !0
    },
    _update: function() {
        return !0
    },
    getBaseLayer: function() {
        return this._baseLayer
    },
    getBounds: function() {
        var a = new L.LatLngBounds;
        return this._currentLayer && a.extend(this._currentLayer.getBounds ? this._currentLayer.getBounds() : this._currentLayer.getLatLng()),
        a
    }
}),
L.timeDimension.layer = function(a, b) {
    return new L.TimeDimension.Layer(a,b)
}
,

L.TimeDimension.Player = (L.Layer || L.Class).extend({
    includes: L.Evented || L.Mixin.Events,
    initialize: function(a, b) {
        L.setOptions(this, a),
        this._timeDimension = b,
        this._paused = !1,
        this._buffer = this.options.buffer || 5,
        this._minBufferReady = this.options.minBufferReady || 1,
        this._waitingForBuffer = !1,
        this._loop = this.options.loop || !1,
        this._steps = 1,
        this._timeDimension.on("timeload", function(a) {
            this.release(),
            this._waitingForBuffer = !1
        }
        .bind(this)),
        this.setTransitionTime(this.options.transitionTime || 1e3),
        this._timeDimension.on("limitschanged availabletimeschanged timeload", function(a) {
            this._timeDimension.prepareNextTimes(this._steps, this._minBufferReady, this._loop)
        }
        .bind(this))
    },
    _tick: function() {
        var a = this._getMaxIndex()
          , b = this._timeDimension.getCurrentTimeIndex() >= a && this._steps > 0
          , c = 0 == this._timeDimension.getCurrentTimeIndex() && this._steps < 0;
        if ((b || c) && !this._loop)
            return this.pause(),
            this.stop(),
            void this.fire("animationfinished");
        if (!this._paused) {
            var d = 0
              , e = this._bufferSize;
            if (this._minBufferReady > 0)
                if (d = this._timeDimension.getNumberNextTimesReady(this._steps, e, this._loop),
                this._waitingForBuffer) {
                    if (e > d)
                        return void this.fire("waiting", {
                            buffer: e,
                            available: d
                        });
                    this.fire("running"),
                    this._waitingForBuffer = !1
                } else if (d < this._minBufferReady)
                    return this._waitingForBuffer = !0,
                    this._timeDimension.prepareNextTimes(this._steps, e, this._loop),
                    void this.fire("waiting", {
                        buffer: e,
                        available: d
                    });
            this.pause(),
            this._timeDimension.nextTime(this._steps, this._loop),
            e > 0 && this._timeDimension.prepareNextTimes(this._steps, e, this._loop)
        }
    },
    _getMaxIndex: function() {
        return Math.min(this._timeDimension.getAvailableTimes().length - 1, this._timeDimension.getUpperLimitIndex() || 1 / 0)
    },
    start: function(a) {
        this._intervalID || (this._steps = a || 1,
        this._waitingForBuffer = !1,
        this.options.startOver && this._timeDimension.getCurrentTimeIndex() === this._getMaxIndex() && this._timeDimension.setCurrentTimeIndex(this._timeDimension.getLowerLimitIndex() || 0),
        this.release(),
        this._intervalID = window.setInterval(L.bind(this._tick, this), this._transitionTime),
        this._tick(),
        this.fire("play"),
        this.fire("running"))
    },
    stop: function() {
        this._intervalID && (clearInterval(this._intervalID),
        this._intervalID = null,
        this._waitingForBuffer = !1,
        this.fire("stop"))
    },
    pause: function() {
        this._paused = !0
    },
    release: function() {
        this._paused = !1
    },
    getTransitionTime: function() {
        return this._transitionTime
    },
    isPlaying: function() {
        return this._intervalID ? !0 : !1
    },
    isWaiting: function() {
        return this._waitingForBuffer
    },
    isLooped: function() {
        return this._loop
    },
    setLooped: function(a) {
        this._loop = a,
        this.fire("loopchange", {
            loop: a
        })
    },
    setTransitionTime: function(a) {
        this._transitionTime = a,
        "function" == typeof this._buffer ? this._bufferSize = this._buffer.call(this, this._transitionTime, this._minBufferReady, this._loop) : this._bufferSize = this._buffer,
        this._intervalID && (this.stop(),
        this.start(this._steps)),
        this.fire("speedchange", {
            transitionTime: a,
            buffer: this._bufferSize
        })
    },
    getSteps: function() {
        return this._steps
    }
}),
L.UI = L.ui = L.UI || {},
L.UI.Knob = L.Draggable.extend({
    options: {
        className: "knob",
        step: 1,
        rangeMin: 0,
        rangeMax: 10
    },
    initialize: function(a, b) {
        L.setOptions(this, b),
        this._element = L.DomUtil.create("div", this.options.className || "knob", a),
        L.Draggable.prototype.initialize.call(this, this._element, this._element),
        this._container = a,
        this.on("predrag", function() {
            this._newPos.y = 0,
            this._newPos.x = this._adjustX(this._newPos.x)
        }, this),
        this.on("dragstart", function() {
            L.DomUtil.addClass(a, "dragging")
        }),
        this.on("dragend", function() {
            L.DomUtil.removeClass(a, "dragging")
        }),
        L.DomEvent.on(this._element, "dblclick", function(a) {
            this.fire("dblclick", a)
        }, this),
        L.DomEvent.disableClickPropagation(this._element),
        this.enable()
    },
    _getProjectionCoef: function() {
        return (this.options.rangeMax - this.options.rangeMin) / (this._container.offsetWidth || this._container.style.width)
    },
    _update: function() {
        this.setPosition(L.DomUtil.getPosition(this._element).x)
    },
    _adjustX: function(a) {
        var b = this._toValue(a) || this.getMinValue();
        return this._toX(this._adjustValue(b))
    },
    _adjustValue: function(a) {
        return a = Math.max(this.getMinValue(), Math.min(this.getMaxValue(), a)),
        a -= this.options.rangeMin,
        a = Math.round(a / this.options.step) * this.options.step,
        a += this.options.rangeMin,
        a = Math.round(100 * a) / 100
    },
    _toX: function(a) {
        var b = (a - this.options.rangeMin) / this._getProjectionCoef();
        return b
    },
    _toValue: function(a) {
        var b = a * this._getProjectionCoef() + this.options.rangeMin;
        return b
    },
    getMinValue: function() {
        return this.options.minValue || this.options.rangeMin
    },
    getMaxValue: function() {
        return this.options.maxValue || this.options.rangeMax
    },
    setStep: function(a) {
        this.options.step = a,
        this._update()
    },
    setPosition: function(a) {
        L.DomUtil.setPosition(this._element, L.point(this._adjustX(a), 0)),
        this.fire("positionchanged")
    },
    getPosition: function() {
        return L.DomUtil.getPosition(this._element).x
    },
    setValue: function(a) {
        this.setPosition(this._toX(a))
    },
    getValue: function() {
        return this._adjustValue(this._toValue(this.getPosition()))
    }
}),
L.Control.TimeDimension = L.Control.extend({
    options: {
        styleNS: "leaflet-control-timecontrol",
        position: "bottomleft",
        title: "Time Control",
        backwardButton: !0,
        forwardButton: !0,
        playButton: !0,
        playReverseButton: !1,
        loopButton: !1,
        displayDate: !0,
        timeSlider: !0,
        timeSliderDragUpdate: !1,
        limitSliders: !1,
        limitMinimumRange: 5,
        speedSlider: !0,
        minSpeed: .1,
        maxSpeed: 10,
        speedStep: .1,
        timeSteps: 1,
        autoPlay: !1,
        playerOptions: {
            transitionTime: 1e3
        }
    },
    initialize: function(a) {
        L.Control.prototype.initialize.call(this, a),
        this._dateUTC = !0,
        this._timeDimension = this.options.timeDimension || null
    },
    onAdd: function(a) {
        var b;
        return this._map = a,
        !this._timeDimension && a.timeDimension && (this._timeDimension = a.timeDimension),
        this._initPlayer(),
        b = L.DomUtil.create("div", "leaflet-bar leaflet-bar-horizontal leaflet-bar-timecontrol"),
        this.options.backwardButton && (this._buttonBackward = this._createButton("Backward", b)),
        this.options.playReverseButton && (this._buttonPlayReversePause = this._createButton("Play Reverse", b)),
        this.options.playButton && (this._buttonPlayPause = this._createButton("Play", b)),
        this.options.forwardButton && (this._buttonForward = this._createButton("Forward", b)),
        this.options.loopButton && (this._buttonLoop = this._createButton("Loop", b)),
        this.options.displayDate && (this._displayDate = this._createButton("Date", b)),
        this.options.timeSlider && (this._sliderTime = this._createSliderTime(this.options.styleNS + " timecontrol-slider timecontrol-dateslider", b)),
        this.options.speedSlider && (this._sliderSpeed = this._createSliderSpeed(this.options.styleNS + " timecontrol-slider timecontrol-speed", b)),
        this._steps = this.options.timeSteps || 1,
        this._timeDimension.on("timeload", this._update, this),
        this._timeDimension.on("timeload", this._onPlayerStateChange, this),
        this._timeDimension.on("timeloading", this._onTimeLoading, this),
        this._timeDimension.on("limitschanged availabletimeschanged", this._onTimeLimitsChanged, this),
        L.DomEvent.disableClickPropagation(b),
        b
    },
    addTo: function() {
        return L.Control.prototype.addTo.apply(this, arguments),
        this._onPlayerStateChange(),
        this._onTimeLimitsChanged(),
        this._update(),
        this
    },
    onRemove: function() {
        this._player.off("play stop running loopchange speedchange", this._onPlayerStateChange, this),
        this._player.off("waiting", this._onPlayerWaiting, this),
        this._timeDimension.off("timeload", this._update, this),
        this._timeDimension.off("timeload", this._onPlayerStateChange, this),
        this._timeDimension.off("timeloading", this._onTimeLoading, this),
        this._timeDimension.off("limitschanged availabletimeschanged", this._onTimeLimitsChanged, this)
    },
    _initPlayer: function() {
        this._player || (this.options.player ? this._player = this.options.player : this._player = new L.TimeDimension.Player(this.options.playerOptions,this._timeDimension)),
        this.options.autoPlay && this._player.start(this._steps),
        this._player.on("play stop running loopchange speedchange", this._onPlayerStateChange, this),
        this._player.on("waiting", this._onPlayerWaiting, this),
        this._onPlayerStateChange()
    },
    _onTimeLoading: function(a) {
        a.time == this._timeDimension.getCurrentTime() && this._displayDate && L.DomUtil.addClass(this._displayDate, "loading")
    },
    _onTimeLimitsChanged: function() {
        var a = this._timeDimension.getLowerLimitIndex()
          , b = this._timeDimension.getUpperLimitIndex()
          , c = this._timeDimension.getAvailableTimes().length - 1;
        this._limitKnobs && (this._limitKnobs[0].options.rangeMax = c,
        this._limitKnobs[1].options.rangeMax = c,
        this._limitKnobs[0].setValue(a || 0),
        this._limitKnobs[1].setValue(b || c)),
        this._sliderTime && (this._sliderTime.options.rangeMax = c,
        this._sliderTime._update())
    },
    _onPlayerWaiting: function(a) {
        this._buttonPlayPause && this._player.getSteps() > 0 && (L.DomUtil.addClass(this._buttonPlayPause, "loading"),
        this._buttonPlayPause.innerHTML = this._getDisplayLoadingText(a.available, a.buffer)),
        this._buttonPlayReversePause && this._player.getSteps() < 0 && (L.DomUtil.addClass(this._buttonPlayReversePause, "loading"),
        this._buttonPlayReversePause.innerHTML = this._getDisplayLoadingText(a.available, a.buffer))
    },
    _onPlayerStateChange: function() {
        if (this._buttonPlayPause && (this._player.isPlaying() && this._player.getSteps() > 0 ? (L.DomUtil.addClass(this._buttonPlayPause, "pause"),
        L.DomUtil.removeClass(this._buttonPlayPause, "play")) : (L.DomUtil.removeClass(this._buttonPlayPause, "pause"),
        L.DomUtil.addClass(this._buttonPlayPause, "play")),
        this._player.isWaiting() && this._player.getSteps() > 0 ? L.DomUtil.addClass(this._buttonPlayPause, "loading") : (this._buttonPlayPause.innerHTML = "",
        L.DomUtil.removeClass(this._buttonPlayPause, "loading"))),
        this._buttonPlayReversePause && (this._player.isPlaying() && this._player.getSteps() < 0 ? L.DomUtil.addClass(this._buttonPlayReversePause, "pause") : L.DomUtil.removeClass(this._buttonPlayReversePause, "pause"),
        this._player.isWaiting() && this._player.getSteps() < 0 ? L.DomUtil.addClass(this._buttonPlayReversePause, "loading") : (this._buttonPlayReversePause.innerHTML = "",
        L.DomUtil.removeClass(this._buttonPlayReversePause, "loading"))),
        this._buttonLoop && (this._player.isLooped() ? L.DomUtil.addClass(this._buttonLoop, "looped") : L.DomUtil.removeClass(this._buttonLoop, "looped")),
        this._sliderSpeed && !this._draggingSpeed) {
            var a = this._player.getTransitionTime() || 1e3;
            a = Math.round(1e4 / a) / 10,
            this._sliderSpeed.setValue(a)
        }
    },
    _update: function() {
        if (this._timeDimension)
            if (this._timeDimension.getCurrentTimeIndex() >= 0) {
                var a = new Date(this._timeDimension.getCurrentTime());
                this._displayDate && (L.DomUtil.removeClass(this._displayDate, "loading"),
                this._displayDate.innerHTML = this._getDisplayDateFormat(a)),
                this._sliderTime && !this._slidingTimeSlider && this._sliderTime.setValue(this._timeDimension.getCurrentTimeIndex())
            } else
                this._displayDate && (this._displayDate.innerHTML = this._getDisplayNoTimeError())
    },
    _createButton: function(a, b) {
        var c = L.DomUtil.create("a", this.options.styleNS + " timecontrol-" + a.toLowerCase(), b);
        return c.href = "#",
        c.title = a,
        L.DomEvent.addListener(c, "click", L.DomEvent.stopPropagation).addListener(c, "click", L.DomEvent.preventDefault).addListener(c, "click", this["_button" + a.replace(/ /i, "") + "Clicked"], this),
        c
    },
    _createSliderTime: function(a, b) {
        var c, d, e, f, g;
        return c = L.DomUtil.create("div", a, b),
        d = L.DomUtil.create("div", "slider", c),
        e = this._timeDimension.getAvailableTimes().length - 1,
        this.options.limitSliders && (g = this._limitKnobs = this._createLimitKnobs(d)),
        f = new L.UI.Knob(d,{
            className: "knob main",
            rangeMin: 0,
            rangeMax: e
        }),
        f.on("dragend", function(a) {
            var b = a.target.getValue();
            this._sliderTimeValueChanged(b),
            this._slidingTimeSlider = !1
        }, this),
        f.on("drag", function(a) {
            this._slidingTimeSlider = !0;
            var b = this._timeDimension.getAvailableTimes()[a.target.getValue()];
            if (b) {
                var c = new Date(b);
                this._displayDate && (this._displayDate.innerHTML = this._getDisplayDateFormat(c)),
                this.options.timeSliderDragUpdate && this._sliderTimeValueChanged(a.target.getValue())
            }
        }, this),
        f.on("predrag", function() {
            var a, b;
            g && (a = g[0].getPosition(),
            b = g[1].getPosition(),
            this._newPos.x < a && (this._newPos.x = a),
            this._newPos.x > b && (this._newPos.x = b))
        }, f),
        L.DomEvent.on(d, "click", function(a) {
            if (!L.DomUtil.hasClass(a.target, "knob")) {
                var b = a.touches && 1 === a.touches.length ? a.touches[0] : a
                  , c = L.DomEvent.getMousePosition(b, d).x;
                g ? g[0].getPosition() <= c && c <= g[1].getPosition() && (f.setPosition(c),
                this._sliderTimeValueChanged(f.getValue())) : (f.setPosition(c),
                this._sliderTimeValueChanged(f.getValue()))
            }
        }, this),
        f.setPosition(0),
        f
    },
    _createLimitKnobs: function(a) {
        L.DomUtil.addClass(a, "has-limits");
        var b = this._timeDimension.getAvailableTimes().length - 1
          , c = L.DomUtil.create("div", "range", a)
          , d = new L.UI.Knob(a,{
            className: "knob lower",
            rangeMin: 0,
            rangeMax: b
        })
          , e = new L.UI.Knob(a,{
            className: "knob upper",
            rangeMin: 0,
            rangeMax: b
        });
        return L.DomUtil.setPosition(c, 0),
        d.setPosition(0),
        e.setPosition(b),
        d.on("dragend", function(a) {
            var b = a.target.getValue();
            this._sliderLimitsValueChanged(b, e.getValue())
        }, this),
        e.on("dragend", function(a) {
            var b = a.target.getValue();
            this._sliderLimitsValueChanged(d.getValue(), b)
        }, this),
        d.on("drag positionchanged", function() {
            L.DomUtil.setPosition(c, L.point(d.getPosition(), 0)),
            c.style.width = e.getPosition() - d.getPosition() + "px"
        }, this),
        e.on("drag positionchanged", function() {
            c.style.width = e.getPosition() - d.getPosition() + "px"
        }, this),
        e.on("predrag", function() {
            var a = d._toX(d.getValue() + this.options.limitMinimumRange);
            e._newPos.x <= a && (e._newPos.x = a)
        }, this),
        d.on("predrag", function() {
            var a = e._toX(e.getValue() - this.options.limitMinimumRange);
            d._newPos.x >= a && (d._newPos.x = a)
        }, this),
        d.on("dblclick", function() {
            this._timeDimension.setLowerLimitIndex(0)
        }, this),
        e.on("dblclick", function() {
            this._timeDimension.setUpperLimitIndex(this._timeDimension.getAvailableTimes().length - 1)
        }, this),
        [d, e]
    },
    _createSliderSpeed: function(a, b) {
        var c = L.DomUtil.create("div", a, b)
          , d = L.DomUtil.create("span", "speed", c)
          , e = L.DomUtil.create("div", "slider", c)
          , f = Math.round(1e4 / (this._player.getTransitionTime() || 1e3)) / 10;
        d.innerHTML = this._getDisplaySpeed(f);
        var g = new L.UI.Knob(e,{
            step: this.options.speedStep,
            rangeMin: this.options.minSpeed,
            rangeMax: this.options.maxSpeed
        });
        return g.on("dragend", function(a) {
            var b = a.target.getValue();
            this._draggingSpeed = !1,
            d.innerHTML = this._getDisplaySpeed(b),
            this._sliderSpeedValueChanged(b)
        }, this),
        g.on("drag", function(a) {
            this._draggingSpeed = !0,
            d.innerHTML = this._getDisplaySpeed(a.target.getValue())
        }, this),
        g.on("positionchanged", function(a) {
            d.innerHTML = this._getDisplaySpeed(a.target.getValue())
        }, this),
        L.DomEvent.on(e, "click", function(a) {
            if (a.target !== g._element) {
                var b = a.touches && 1 === a.touches.length ? a.touches[0] : a
                  , c = L.DomEvent.getMousePosition(b, e).x;
                g.setPosition(c),
                d.innerHTML = this._getDisplaySpeed(g.getValue()),
                this._sliderSpeedValueChanged(g.getValue())
            }
        }, this),
        g
    },
    _buttonBackwardClicked: function() {
        this._timeDimension.previousTime(this._steps)
    },
    _buttonForwardClicked: function() {
        this._timeDimension.nextTime(this._steps)
    },
    _buttonLoopClicked: function() {
        this._player.setLooped(!this._player.isLooped())
    },
    _buttonPlayClicked: function() {
        this._player.isPlaying() ? this._player.stop() : this._player.start(this._steps)
    },
    _buttonPlayReverseClicked: function() {
        this._player.isPlaying() ? this._player.stop() : this._player.start(-1 * this._steps)
    },
    _buttonDateClicked: function() {
        this._toggleDateUTC()
    },
    _sliderTimeValueChanged: function(a) {
        this._timeDimension.setCurrentTimeIndex(a)
    },
    _sliderLimitsValueChanged: function(a, b) {
        this._timeDimension.setLowerLimitIndex(a),
        this._timeDimension.setUpperLimitIndex(b)
    },
    _sliderSpeedValueChanged: function(a) {
        this._player.setTransitionTime(1e3 / a)
    },
    _toggleDateUTC: function() {
        this._dateUTC ? (L.DomUtil.removeClass(this._displayDate, "utc"),
        this._displayDate.title = "Local Time") : (L.DomUtil.addClass(this._displayDate, "utc"),
        this._displayDate.title = "UTC Time"),
        this._dateUTC = !this._dateUTC,
        this._update()
    },
    _getDisplayDateFormat: function(a) {
        return this._dateUTC ? a.toISOString().slice(0,4) : a.toLocaleString().slice(6,10)
    },
    _getDisplaySpeed: function(a) {
        return a + "fps"
    },
    _getDisplayLoadingText: function(a, b) {
        return "<span>" + Math.floor(a / b * 100) + "%</span>"
    },
    _getDisplayNoTimeError: function() {
        return "Time not available"
    }
}),
L.Map.addInitHook(function() {
    this.options.timeDimensionControl && (this.timeDimensionControl = L.control.timeDimension(this.options.timeDimensionControlOptions || {}),
    this.addControl(this.timeDimensionControl))
}),
L.control.timeDimension = function(a) {
    return new L.Control.TimeDimension(a)
}
;
