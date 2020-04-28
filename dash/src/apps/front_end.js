import { App } from '../apps/app';
import { GetAlgorithm } from '../algo/selector';

import { Decision } from '../common/data';
import { logging, exportLogs } from '../common/logger';
import { Metrics, StatsTracker } from '../component/stats'; 
import { SetQualityController, onEvent } from '../component/abr';
import { Interceptor } from '../component/intercept';

import { QualityController } from '../controller/quality';
import { StatsController } from '../controller/stats';


const logger = logging('App');


export class FrontEndApp extends App {
    constructor(player, recordMetrics, shim, name, videoInfo) {
        super(player);

        this.tracker = new StatsTracker(player);
        this.interceptor = new Interceptor(videoInfo);
        this.shim = shim;
        
        this.statsController = new StatsController();
        this.qualityController = new QualityController();
        this.algorithm = GetAlgorithm(name, shim, videoInfo);

        this.recordMetrics = recordMetrics;

        SetQualityController(this.qualityController);
    }

    start() {
        logger.log("Starting App.")
        this.qualityController
            .onGetQuality((index) => {
                this.tracker.getMetrics();
                let controller = this.qualityController;
                
                let metrics = this.statsController.metrics;
                let timestamp = (metrics.playerTime.slice(-1)[0] || {'timestamp' : 0}).timestamp;
                this.statsController.advance(timestamp);
                
                if (this.recordMetrics) {
                    this.shim
                        .metricsLoggingRequest()
                        .addStats(metrics.serialize(true))
                        .send();
                }
                
                let decision = this.algorithm.getDecision(
                    metrics,
                    index,
                    timestamp,
                );
                controller.addPiece(decision);
            });

        let eos = (context) => {
            logger.log('End of stream');
            if (this.recordMetrics) {
                let logs = exportLogs();  
                this.shim
                    .metricsLoggingRequest()
                    .addLogs(logs)
                    .addComplete()
                    .send();
            }
        };
        onEvent("endOfStream", (context) => eos(context));
        onEvent("PLAYBACK_ENDED", (context) => eos(context));

        onEvent("Detected unintended removal", (context) => {
            logger.log('Wtf');
           
            let controller = context.scheduleController;
            controller.start();
        });
        
        this.interceptor
            .onRequest((ctx, index) => {
                this.algorithm.newRequest(ctx);

                logger.log('Advance', index + 1);
                this.qualityController.advance(index + 1);
                this.tracker.getMetrics(); 
            })
            .start();
        
        this.tracker.registerCallback((metrics) => {
            this.statsController.addMetrics(metrics);
        });

        this.tracker.start();
    }
}
