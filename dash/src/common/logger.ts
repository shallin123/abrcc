import { Dict } from '../types';
import { timestamp as create_timestamp } from '../common/time';


const loggers: Dict<string, Logger> = {};
const central_log = new class {
    _log: Array<string>;

    constructor() {
        this._log = [];
    }

    log(logname: string, args: Array<any>) {
        let timestamp: number = create_timestamp(new Date());
        let toLog: string = `[${logname}] ${timestamp}`;
        for (let arg of args) {
            toLog = toLog.concat(" | "); 
            if (typeof arg === 'string') {
                toLog = toLog.concat(arg);
            } else {
                toLog = toLog.concat(JSON.stringify(arg));
            }
        }
        this._log.push(toLog);
    }

    getLogs(): Array<string> {
        return [...this._log];
    }
}();


export function exportLogs(): Array<string> {
    return central_log.getLogs();
}


function hashCode(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
       hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    return hash;
} 

function intToRGB(i: number): string {
    let c = (i & 0x00FFFFFF).toString(16).toUpperCase();
    return "00000".substring(0, 6 - c.length) + c;
}

/**
 * Class that allows logging a variable number of `any` arguments.
 */
export class Logger {
    logName: string;
    color: string;
    
    constructor(logName: string) {
        this.logName = logName;
        this.color = intToRGB(hashCode(logName));
    }

    log(...args: any[]): void {
        let toLog = [
            `%c  ${this.logName}  `,
            `color: white; background-color: #${this.color}`,
        ];
        for (let argument of args) {
            toLog.push(" | "); 
            toLog.push(argument);
        }
        console.log(...toLog);
        central_log.log(this.logName, args);    
    }
}

/**
 * Given a project-wide `logName`, create a logger associated with the `logName` to be 
 * used in the file in which the logging functionality is invoked.
 *
 * Usage:
 *   const logger = logging('example');
 *      [...]
 *   logger.log('a', 123, {'an' : 'object'});
 */
export function logging(logName: string): Logger {   
    if (loggers[logName] === undefined) {
        loggers[logName] = new Logger(logName);
    }
    return loggers[logName];
}
