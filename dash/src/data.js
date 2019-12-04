const MAX_QUALITY = 5; // 0 -> 6


export class Piece {
    get index() {
        throw new TypeError("not implemented error")
    }

    get timestamp() {
        throw new TypeError("not implemented error")
    }
}


export class Value {
    constructor(value, timestamp) {
        this._value = value;
        this._timestamp = new Date().getTime();
    }

    withTimestamp(timestamp) {
        this._timestamp = timestamp;
        return this;
    }

    get value() {
        return this._value;
    }

    get timestamp() {
        return this._timestamp;
    }
}


export class Segment extends Piece {
    constructor() {
        super()
        this._timestamp = new Date().getTime();
    }

    withTimestamp(timestamp) {
        this._timestamp = timestamp;
        return this;
    }

    withQuality(quality) {
        this._quality = quality;
        return this;
    }

    withState(state) {
        this._state = state;
        return this;
    }
   
    withIndex(startTime, duration) {
        // segments start from 1
        this._index = Math.round(startTime / duration);
        return this;
    }

    // assumes format [domain]/video[quality]/[segment].[type]
    withUrl(url) {
        let split = url.split('/');
        
        let raw_quality = split[split.length - 2];
        let quality = parseInt(raw_quality.substring(5), 10); 
        
        let raw_segment = split[split.length - 1];
        let segment = parseInt(raw_segment.split('.')[0], 10);
    
        this._quality = MAX_QUALITY - quality + 1;
        this._index = segment;
        this._state = 'downloaded';
        
        return this;
    }

    get timestamp() {
        return this._timestamp;
    }

    get index() {
        return this._index;
    }

    get quality() {
        return this._quality;
    }

    get state() { 
        return this._state;
    }
}



