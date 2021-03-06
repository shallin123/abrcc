from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import List, Optional
from statistics import stdev

from abr.video import get_video_chunks
from exp_util.env import experiments, experiment, run_subexp, run_trace, run_traffic
from exp_util.data import Experiment, save_experiments, generate_summary, load_experiments
from exp_util.plot import plot_bar, plot_cdf, plot_fct_cdf, plot_tag, plot_flow_capacity_cdf

import os
import time
import random


@experiment
def minerva_example(args: Namespace) -> None:
    experiments = []
    root_path = str(Path("test"))
    os.system(f"mkdir -p {root_path}")
   
    latency, bandwidth = 500, 1
    name = 'minerva' 
    algo = 'minerva'
    cc   = 'minerva'
    
    experiment_path = str(Path(root_path)) 
    subpath = str(Path(experiment_path) / "minerva")
    
    server1 = f"--cc {cc} --algo {algo} --server-algo {algo} --name minerva1 --video guard"
    server2 = f"--cc {cc} --algo {algo} --server-algo {algo} --name minerva2 --video bojack"
    
    path = subpath
    run_subexp(bandwidth, latency, path, [server1, server2], burst=2000, video='bojack', force_run=True)


@experiment
def autotarget_training(args: Namespace) -> None:
    videos = ['bojack', 'guard']

    experiments = []
    root_path = str(Path("test"))
    os.system(f"mkdir -p {root_path}")
   
    compete1 = [
        ('dynamic', 'bbr2'),
    ]
    compete2 = [
        ('remote', 'target')
    ]

    for run_id in range(100):
        for video in videos:
            experiment_path = str(Path(root_path) / video)
            latency = 500
            for bandwidth in [1, 2, 3]:
                subpath = str(Path(experiment_path) / "versus_rmpc")
                for (algo1, cc1) in compete1:
                    for (algo2, cc2) in compete2:
                        server1 = f"--algo {algo1} --name robustMpc --cc {cc1} --video {video} --training" 
                        server2 = f"--server-algo {algo2} --name abrcc --cc {cc2} --video {video} --training"
                        
                        path = str(Path(subpath) / f"{cc1}_{algo2}_{cc2}_{bandwidth}_run{run_id}")
                        run_subexp(
                            bandwidth, latency, path, [server1, server2], burst=2000, video=video, force_run=True,
                        )

@experiment
def single_flow_traffic(args: Namespace) -> None:
    global run_traffic
    if args.dry:
        run_traffic = lambda *args, **kwargs: None 

    videos = ['got', 'bojack', 'cook', 'guard']

    root_path = str(Path("experiments") / "traffic")
    os.system(f"mkdir -p {root_path}")
    runner_log = open(str(Path(root_path) / 'exp.log'), 'w')
   
    instances = [
        ('--algo', 'robustMpc', 'cubic'),
        ('--server-algo', 'gap', 'gap'),
        ('--algo', 'dynamic', 'bbr2'),
        ('--algo', 'robustMpc', 'bbr2'),
        ('--algo', 'dynamic', 'cubic'),
    ]

    experiments = []
    experiment_path = str(Path(root_path) / 'sft')
    subpath = experiment_path
    latency = 500
    for bandwidth in [2, 3, 4]:
        for (where, algo, cc) in instances:
            for run_id in range(4):
                for video in videos:
                    server = f"{where} {algo} --name abr --cc {cc} --video {video}" 
                    path = str(Path(subpath) / f"{algo}_{cc}_{bandwidth}_{video}_run{run_id}")
                    
                    runner_log.write(f'> {path}\n')
                    run_traffic(path, f"{server} -l {latency} -b {bandwidth} --single-flow", headless=args.headless)
                   
                    cc_name = cc if cc != "gap" else "gap2"
                    experiments.append(Experiment(
                        video = video,
                        path = str(Path(path) / "abr_plots.log"),
                        latency = latency,
                        bandwidth = bandwidth,
                        extra = ["sf", algo, cc_name, f"bw{bandwidth}"],
                        run_id = run_id,
                    ))
    if args.dry:
        print(experiments)
        print(len(experiments))
    else:
        save_experiments(experiment_path, experiments)
        generate_summary(experiment_path, experiments)
  

@experiment
def traffic(args: Namespace) -> None:
    global run_traffic
    if args.dry:
        run_traffic = lambda *args, **kwargs: None 

    videos = ['got', 'bojack', 'cook', 'guard']

    root_path = str(Path("experiments") / "traffic")
    os.system(f"mkdir -p {root_path}")
    runner_log = open(str(Path(root_path) / 'exp.log'), 'w')
   
    instances = [
        ('--algo', 'robustMpc', 'cubic'),
        ('--algo', 'robustMpc', 'bbr2'),
        ('--algo', 'dynamic', 'bbr2'),
        ('--algo', 'dynamic', 'cubic'),
        ('--server-algo', 'gap', 'gap'),
    ]

    experiments = []
    experiment_path = str(Path(root_path) / 'fct')
    subpath = experiment_path
    latency = 100
    for bandwidth in [5, 4, 3]:
        for (where, algo, cc) in instances:
            for run_id in range(10):
                video = random.choice(videos)

                server = f"{where} {algo} --name abr --cc {cc} --video {video}" 
                path = str(Path(subpath) / f"{algo}_{cc}_{bandwidth}_run{run_id}")
                
                runner_log.write(f'> {path}\n')
                run_traffic(path, f"{server} -l {latency} -b {bandwidth} --light", headless=args.headless, burst=20000)
               
                cc_name = cc if cc != "gap" else "gap2"
                experiments.append(Experiment(
                    video = video,
                    path = str(Path(path) / "abr_plots.log"),
                    latency = latency,
                    bandwidth = bandwidth,
                    extra = ["fct", algo, cc_name, f"bw{bandwidth}"],
                    run_id = run_id,
                ))
    if args.dry:
        print(experiments)
        print(len(experiments))
    else:
        save_experiments(experiment_path, experiments)
        generate_summary(experiment_path, experiments)
   
    latency = 100
    for video in videos:
        experiments = []
        experiment_path = str(Path(root_path) / video)
        for run_id in range(4):
            for bandwidth in [3, 2, 1]:
                # versus 
                subpath = str(Path(experiment_path) / "versus_rmpc")
                for (where, algo, cc) in instances:
                    server = f"{where} {algo} --name abr --cc {cc} --video {video}" 
                    path = str(Path(subpath) / f"{algo}_{cc}_{bandwidth}_run{run_id}")
                    
                    runner_log.write(f'> {path}\n')
                    run_traffic(path, f"{server} -l {latency} -b {bandwidth}", headless=args.headless)
                    
                    if cc == "gap":
                        cc = "gap2"
                    experiments.append(Experiment(
                        video = video,
                        path = str(Path(path) / "abr_plots.log"),
                        latency = latency,
                        bandwidth = bandwidth,
                        extra = ["traffic", algo, cc, video],
                        run_id = run_id,
                    ))
        
        if args.dry:
            print(experiments)
            print(len(experiments))
        else:
            save_experiments(experiment_path, experiments)
            generate_summary(experiment_path, experiments)


@experiment
def stream_count(args: Namespace) -> None:
    global run_trace, run_subexp
    if args.dry:
        run_trace  = lambda *args, **kwargs: None
        run_subexp = lambda *args, **kwargs: None 

    videos = ['got', 'bojack', 'cook', 'guard']

    root_path = str(Path("experiments") / "stream_count")
    os.system(f"mkdir -p {root_path}")
    runner_log = open(str(Path(root_path) / 'exp.log'), 'w')
   
    algorithms = [
        ('--server-algo', 'minerva', 'minerva'),
        ('--server-algo', 'minervann', 'minerva'),
        ('--server-algo', 'gap', 'gap'),
        ('--algo', 'robustMpc', 'cubic'),
        ('--algo', 'robustMpc', 'bbr2'),
        ('--algo', 'dynamic', 'bbr2'),
        ('--algo', 'dynamic', 'cubic'),
    ]

    experiments = []
    experiment_path = str(Path(root_path))
    
    runs      = 20
    latency   = 500
    bandwidth = 4
    min_streams, max_streams = 2, 8

    for stream_number in range(max_streams, min_streams - 1, -1): 
        for run_id in range(runs):
            for (arg, algo, cc) in algorithms:
                run_servers = []
                run_videos  = []
                for i in range(stream_number):
                    video  = random.choice(videos)
                    server = f"{arg} {algo} --name abr{i + 1} --cc {cc} --video {video}"
                    if algo == "minerva" or algo == "minervann":
                        server += f" --algo {algo}"
                    run_videos.append(video)
                    run_servers.append(server)
                
                video_length  = list(zip(map(get_video_chunks, run_videos), run_videos))
                shortest_video = min(video_length)[1]

                path = str(Path(experiment_path) / f"{algo}_{cc}_streams{stream_number}_run{run_id}")
                runner_log.write(f'> {path}\n')
                
                run_subexp(
                   bandwidth, latency, path, run_servers, burst=2000, video=shortest_video,
                   headless=args.headless, 
                )
                experiments.append(Experiment(
                    video = video,
                    path  = str(Path(path) / "leader_plots.log"),
                    latency = latency,
                    bandwidth = bandwidth, 
                    extra = [f"streams{stream_number}", algo, cc],
                    run_id = run_id,
                ))
        
    if args.dry:
        print(experiments)
        print(len(experiments))
    else:
        save_experiments(experiment_path, experiments)
        generate_summary(experiment_path, experiments)


@experiment
def multiple(args: Namespace) -> None:
    global run_trace, run_subexp
    if args.dry:
        run_trace  = lambda *args, **kwargs: None
        run_subexp = lambda *args, **kwargs: None 

    videos = ['got', 'bojack', 'cook', 'guard']

    root_path = str(Path("experiments") / "multiple_videos")
    os.system(f"mkdir -p {root_path}")
    runner_log = open(str(Path(root_path) / 'exp.log'), 'w')
   
    compete1 = [
        ('robustMpc', 'cubic'),
        ('robustMpc', 'bbr2'),
        ('dynamic', 'bbr2'),
        ('dynamic', 'cubic'),
    ]
    compete2 = [
        ('gap', 'gap'),
    ]
    minerva = [
        ('minervann', 'minerva'),
        ('minerva', 'minerva'),
    ]

    for video in videos:
        experiments = []
        experiment_path = str(Path(root_path) / video)
        for run_id in range(4):
            latency = 500
            for bandwidth in [3, 2, 1]:
                # versus 
                subpath = str(Path(experiment_path) / "versus_rmpc")
                for (algo1, cc1) in compete1:
                    for (algo2, cc2) in compete2:
                        server1 = f"--algo {algo1} --name robustMpc --cc {cc1} --video {video}" 
                        server2 = f"--server-algo {algo2} --name abrcc --cc {cc2} --video {video}"
                        
                        path = str(Path(subpath) / f"{cc1}_{algo2}_{cc2}_{bandwidth}_run{run_id}")
                        if algo1 != 'robustMpc': # since we don't want to repet old experiments
                            path = str(Path(subpath) / f"{algo1}_{cc1}_{algo2}_{cc2}_{bandwidth}_run{run_id}")
                        runner_log.write(f'> {path}\n')
                        
                        run_subexp(
                            bandwidth, latency, path, [server1, server2], burst=2000, video=video,
                            headless=args.headless
                        )
                        
                        if cc2 == "gap":
                            cc2 = "gap2"
                        experiments.append(Experiment(
                            video = video,
                            path = str(Path(path) / "leader_plots.log"),
                            latency = latency,
                            bandwidth = bandwidth,
                            extra = ["versus", algo1, cc1, algo2, cc2, video],
                            run_id = run_id,
                        ))

                # self
                subpath = str(Path(experiment_path) / "versus_self")
                for (algo, cc) in compete2 + minerva:
                    server1 = f"--server-algo {algo} --name abrcc1 --cc {cc} --video {video}"
                    server2 = f"--server-algo {algo} --name abrcc2 --cc {cc} --video {video}"
                    if algo == "minerva" or algo == "minervann":
                        server1 += f" --algo {algo}"
                        server2 += f" --algo {algo}"

                    path = str(Path(subpath) / f"{algo}_{cc}_{bandwidth}_run{run_id}")
                    runner_log.write(f'> {path}\n')
                    run_subexp(
                        bandwidth, latency, path, [server1, server2], burst=2000, video=video,
                        headless=args.headless
                    )
                    
                    if cc == "gap":
                        cc = "gap2"
                    experiments.append(Experiment(
                        video = video,
                        path = str(Path(path) / "leader_plots.log"),
                        latency = latency,
                        bandwidth = bandwidth,
                        extra = ["self", algo, cc],
                        run_id = run_id,
                    ))

                # baselines
                subpath = str(Path(experiment_path) / "rmpc")
                for cc1, cc2 in [('cubic', 'bbr2'), ('bbr2', 'bbr2'), ('cubic', 'cubic')]:
                    for algo in ['robustMpc', 'dynamic']:
                        server1 = f"--algo {algo} --name rmpc1 --cc {cc1} --video {video}"
                        server2 = f"--algo {algo} --name rmpc2 --cc {cc2} --video {video}"

                        path = str(Path(subpath) / f"{cc1}_{cc2}_{bandwidth}_run{run_id}")
                        if algo != 'robustMpc': # since we don't want to repet old experiments
                            path = str(Path(subpath) / f"{algo}_{cc1}_{algo2}_{cc2}_{bandwidth}_run{run_id}")
                        runner_log.write(f'> {path}\n')
                        run_subexp(
                            bandwidth, latency, path, [server1, server2], burst=2000, video=video,
                            headless=args.headless
                        )

                        extra = 'rmpc'
                        if algo == 'dynamic':
                            extra = 'dynamic'
                        
                        experiments.append(Experiment(
                            video = video,
                            path = str(Path(path) / "leader_plots.log"),
                            latency = latency,
                            bandwidth = bandwidth,
                            extra = [extra, cc1 + '1', cc2 + '2', video],
                            run_id = run_id,
                        ))
        
        # traces
        subpath = str(Path(experiment_path) / "traces")
        server1 = f"--cc target --server-algo target2 --name abrcc --video {video}"
        server2 = f"--cc bbr2 --algo robustMpc --name robustMpc --video {video}"
        server6 = f"--cc bbr2 --algo dynamic --name dynamic --video {video}"
        server3 = f"--cc gap --server-algo gap --name abrcc --video {video}"
        server4 = f"--cc gap --server-algo remote --name abrcc --video {video}"
        server5 = f"--cc cubic --algo robustMpc --name robustMpc --video {video}"
        for plot_name, name, server in [
            ("robustMpc", "rmpc_bbr", server2), 
            ("robustMpc", "rmpc_cubic", server5), 
            ("dynamic", "dynamic_bbr", server6), 
            ("abrcc", "target2", server1),
            ("abrcc", "gap_pid", server3), 
            ("abrcc", "remote", server4),
        ]:
            traces = Path("network_traces")
            for trace in [
                str(traces / "norway_train_13.txt"),
                
                str(traces / "car.txt"), 
                str(traces / "bus.txt"), 
                str(traces / "bus1.txt"), 
                
                str(traces / "norway_train_6.txt"),

                str(traces / "norway_ferry_11.txt"), 
                str(traces / "norway_ferry_20.txt"),
                str(traces / "norway_ferry_6.txt"),
                
                str(traces / "norway_metro_6.txt"),
                str(traces / "norway_tram_5.txt"),
                str(traces / "norway_tram_14.txt"),
                
                str(traces / "norway_tram_16.txt"),
                str(traces / "norway_tram_19.txt"),
            ]:
                trace_name = trace.split('/')[-1].split('.')[0]
                path = str(Path(subpath) / f'{name}_{trace_name}')
                runner_log.write(f'> {path}\n')
                run_trace(path, f"{server} -l {latency} -t {trace}", headless=args.headless)
                experiments.append(Experiment(
                    video = video,
                    path = str(Path(path) / f"{plot_name}_plots.log"),
                    latency = latency,
                    trace = trace,
                    extra = ["traces", name, trace, run_id],
                    run_id = run_id,
                ))
        if args.dry:
            print(experiments)
            print(len(experiments))
        else:
            save_experiments(experiment_path, experiments)
            generate_summary(experiment_path, experiments)



@experiment
def multiple2(args: Namespace) -> None:
    global run_trace, run_subexp
    if args.dry:
        run_trace  = lambda *args, **kwargs: None
        run_subexp = lambda *args, **kwargs: None 

    videos = ['got', 'bojack', 'cook', 'guard']

    root_path = str(Path("experiments") / "multiple_videos2")
    os.system(f"mkdir -p {root_path}")
    runner_log = open(str(Path(root_path) / 'exp.log'), 'w')
   
    compete1 = [
        ('robustMpc', 'cubic'),
        ('robustMpc', 'bbr2'),
        ('dynamic', 'bbr2'),
        ('dynamic', 'cubic'),
    ]
    compete2 = [
        ('gap', 'gap'),
    ]

    for video in videos:
        experiments = []
        experiment_path = str(Path(root_path) / video)
        for run_id in range(4):
            latency = 500
            for bandwidth in [4, 3, 2]:
                # versus 
                subpath = str(Path(experiment_path) / "versus")
                for (algo1, cc1) in compete1:
                    for (algo2, cc2) in compete2:
                        server1 = f"--algo {algo1} --name robustMpc --cc {cc1} --video {video}" 
                        server3 = f"--algo {algo1} --name robustMpc2 --cc {cc1} --video {video}" 
                        server2 = f"--server-algo {algo2} --name abrcc --cc {cc2} --video {video}"
                        
                        path = str(Path(subpath) / f"{cc1}_{algo2}_{cc2}_{bandwidth}_run{run_id}")
                        if algo1 != 'robustMpc': # since we don't want to repet old experiments
                            path = str(Path(subpath) / f"{algo1}_{cc1}_{algo2}_{cc2}_{bandwidth}_run{run_id}")
                        runner_log.write(f'> {path}\n')
                        
                        run_subexp(
                            bandwidth, latency, path, [server1, server3, server2], burst=2000, video=video,
                            headless=args.headless
                        )
                        
                        if cc2 == "gap":
                            cc2 = "gap2"
                        experiments.append(Experiment(
                            video = video,
                            path = str(Path(path) / "leader_plots.log"),
                            latency = latency,
                            bandwidth = bandwidth,
                            extra = ["versus", algo1, cc1, algo2, cc2, video],
                            run_id = run_id,
                        ))

                # same type
                subpath = str(Path(experiment_path) / "rmpc")
                for cc in ['cubic', 'bbr2']:
                    for algo in ['robustMpc', 'dynamic']:
                        server1 = f"--algo {algo} --name rmpc1 --cc {cc} --video {video}"
                        server2 = f"--algo {algo} --name rmpc2 --cc {cc} --video {video}"
                        server3 = f"--algo {algo} --name rmpc3 --cc {cc} --video {video}"

                        path = str(Path(subpath) / f"{cc}_{bandwidth}_run{run_id}")
                        if algo != 'robustMpc': # since we don't want to repet old experiments
                            path = str(Path(subpath) / f"{algo}_{cc}_{bandwidth}_run{run_id}")
                        runner_log.write(f'> {path}\n')
                        run_subexp(
                            bandwidth, latency, path, [server1, server2, server3], burst=2000, video=video,
                            headless=args.headless
                        )

                        extra = 'rmpc'
                        if algo == 'dynamic':
                            extra = 'dynamic'
                       
                        experiments.append(Experiment(
                            video = video,
                            path = str(Path(path) / "leader_plots.log"),
                            latency = latency,
                            bandwidth = bandwidth,
                            extra = [extra, cc + '1', cc + '2', cc + '3', video],
                            run_id = run_id,
                        ))

                # minerva
                for cc, algo in [
                    ("minerva", "minerva"),
                    ("minerva", "minervann"),
                ]:
                    server1 = f"--algo {algo} --server-algo {algo} --name rmpc1 --cc {cc} --video {video}"
                    server2 = f"--algo {algo} --server-algo {algo} --name rmpc2 --cc {cc} --video {video}"
                    server3 = f"--algo {algo} --server-algo {algo} --name rmpc3 --cc {cc} --video {video}"
                    path = str(Path(subpath) / f"{algo}_{cc}_{bandwidth}_run{run_id}")
                    runner_log.write(f'> {path}\n')
                    run_subexp(
                        bandwidth, latency, path, [server1, server2, server3], burst=2000, video=video,
                        headless=args.headless
                    )
                    experiments.append(Experiment(
                        video = video,
                        path = str(Path(path) / "leader_plots.log"),
                        latency = latency,
                        bandwidth = bandwidth,
                        extra = [algo, cc + '1', cc + '2', cc + '3', video],
                        run_id = run_id,
                    ))
        
        if args.dry:
            print(experiments)
            print(len(experiments))
        else:
            save_experiments(experiment_path, experiments)
            generate_summary(experiment_path, experiments)


@experiment
def hetero(args: Namespace) -> None:
    global run_trace, run_subexp
    if args.dry:
        run_trace  = lambda *args, **kwargs: None
        run_subexp = lambda *args, **kwargs: None 

    videos = ['got', 'bojack', 'guard']

    root_path = str(Path("experiments") / "hetero")
    os.system(f"mkdir -p {root_path}")
    runner_log = open(str(Path(root_path) / 'exp.log'), 'w')
    
    # only for rmpc at the moment
    compete1 = [
        ('robustMpc', 'bbr2'),
        ('dynamic', 'bbr2'),
        ('robustMpc', 'cubic'),
        ('dynamic', 'cubic'), 
    ]
    compete2 = [
        ('gap', 'gap'),
    ]
    minerva = [
        ('minerva', 'minerva'),
        ('minervann', 'minerva'),
    ]

    for i, video1 in enumerate(videos):
        for j, video2 in enumerate(videos):
            if i != j:
                shorter_video = video1 if get_video_chunks(video1) < get_video_chunks(video2) else video2
                experiments = []
                experiment_path = str(Path(root_path) / f"{video1}_{video2}")
                for run_id in range(4):
                    latency = 500
                    # robustMpc vs others 
                    for bandwidth in [3, 2, 1]:
                        subpath = str(Path(experiment_path) / "versus_rmpc")
                        for (algo1, cc1) in compete1:
                            for (algo2, cc2) in compete2:
                                server1 = f"--algo {algo1} --name robustMpc --cc {cc1} --video {video1}" 
                                server2 = f"--server-algo {algo2} --name abrcc --cc {cc2} --video {video2}"
                        
                                path = str(Path(subpath) / f"{cc1}_{algo2}_{cc2}_{bandwidth}_run{run_id}")
                                if algo1 != 'robustMpc': # since we don't want to repet old experiments
                                    path = str(Path(subpath) / f"{algo1}_{cc1}_{algo2}_{cc2}_{bandwidth}_run{run_id}")
                                runner_log.write(f'> {path}\n')
                       
                                run_subexp(
                                    bandwidth, latency, path, [server1, server2], burst=2000, video=shorter_video,
                                    headless=args.headless
                                )
                                if cc2 == "gap":
                                    cc2 = "gap2"
                                experiments.append(Experiment(
                                    video = shorter_video,
                                    path = str(Path(path) / "leader_plots.log"),
                                    latency = latency,
                                    bandwidth = bandwidth,
                                    extra = ["versus", algo1, cc1, algo2, cc2, f"{video1}1", f"{video2}2"],
                                    run_id = run_id,
                                ))

                        # self
                        subpath = str(Path(experiment_path) / "versus_self") 
                        for (algo, cc) in compete2 + minerva:
                            server1 = f"--server-algo {algo} --name abrcc1 --cc {cc} --video {video1}"
                            server2 = f"--server-algo {algo} --name abrcc2 --cc {cc} --video {video2}"
                            if algo == "minerva" or algo == "minervann":
                                server1 += f" --algo {algo}"
                                server2 += f" --algo {algo}"
                        
                            path = str(Path(subpath) / f"{algo}_{cc}_{bandwidth}_run{run_id}")
                            runner_log.write(f'> {path}\n')
                            run_subexp(
                                bandwidth, latency, path, [server1, server2], burst=2000, video=shorter_video, 
                                headless=args.headless
                            )
                        
                            if cc == "gap":
                                cc = "gap2"
                            experiments.append(Experiment(
                                video = shorter_video,
                                path = str(Path(path) / "leader_plots.log"),
                                latency = latency,
                                bandwidth = bandwidth,
                                extra = ["self", algo, cc, f"{video1}1", f"{video2}"],
                                run_id = run_id,
                            ))

                        # robustMpc
                        subpath = str(Path(experiment_path) / "rmpc")
                        for cc1, cc2 in [('cubic', 'bbr2'), ('bbr2', 'bbr2'), ('cubic', 'cubic')]:
                            for algo in ['robustMpc', 'dynamic']:
                                server1 = f"--algo {algo} --name rmpc1 --cc {cc1} --video {video1}"
                                server2 = f"--algo {algo} --name rmpc2 --cc {cc2} --video {video2}"

                                path = str(Path(subpath) / f"{cc1}_{cc2}_{bandwidth}_run{run_id}")
                                if algo != 'robustMpc': # since we don't want to repet old experiments
                                    path = str(Path(subpath) / f"{algo}_{cc1}_{cc2}_{bandwidth}_run{run_id}")

                                runner_log.write(f'> {path}\n')
                                run_subexp(
                                    bandwidth, latency, path, [server1, server2], burst=2000, video=shorter_video,
                                    headless=args.headless
                                )
                                extra = 'rmpc'
                                if algo == 'dynamic':
                                    extra = 'dynamic'
     
                                experiments.append(Experiment(
                                    video = shorter_video,
                                    path = str(Path(path) / "leader_plots.log"),
                                    latency = latency,
                                    bandwidth = bandwidth,
                                    extra = [extra, cc1 + '1', cc2 + '2', f"{video1}1", f"{video2}2"],
                                    run_id = run_id,
                                ))
                if args.dry:
                    print(experiments)
                    print(len(experiments))
                else:
                    save_experiments(experiment_path, experiments)
                    generate_summary(experiment_path, experiments)


@experiment
def generate_plots(args: Namespace) -> None:
    avg = lambda xs: sum(xs) / len(xs)
    cap = lambda xs: max(xs + [-50])
    cv = lambda xs: stdev(xs) / avg(xs)

    def plot_multiple(path: str, experiments: List[Experiment], cc: str) -> None:
        plot_bar(path, experiments, [
            # performance
            (["versus", "robustMpc", f"{cc}", "gap2"], (avg, "Gap-RobustMpc", 1) ),
            (["versus", "dynamic", f"{cc}", "gap2"], (avg, "Gap-Dynamic", 1) ),
            (["rmpc", f"{cc}1", f"{cc}2", f"{cc}3"], (avg, "RobustMpc", 1) ),
            (["dynamic", f"{cc}1", f"{cc}2", f"{cc}3"], (avg, "Dynamic", 1) ),
    
            # fairness
            (["versus", "robustMpc", f"{cc}", "gap2"], ('abrcc', "Gap-RobustMpc", 2) ),
            (["versus", "dynamic", f"{cc}", "gap2"], ('abrcc', "Gap-Dynamic", 2) ),
            (["rmpc", f"{cc}1", f"{cc}2", f"{cc}3"], (min, "RobustMpc", 2) ),
            (["dynamic", f"{cc}1", f"{cc}2", f"{cc}3"], (min, "Dynamic", 2) ),
        ], x_range = ["4Mbps", "3Mbps", "2Mbps"], 
           metrics=["vmaf_qoe"], y_labels={'vmaf_qoe' : 'QoE'}, legend_location=4,
        )
    
    def plot_versus(path: str, experiments: List[Experiment], cc: str, **kwargs) -> None:
        plot_bar(path, experiments, [
            # performance
            (["versus", "robustMpc", f"{cc}", "gap2"], ("abrcc", "Gap-RobustMpc", 1) ),
            (["versus", "dynamic", f"{cc}", "gap2"], ("abrcc", "Gap-Dynamic", 1) ),
            (["rmpc", f"{cc}1", f"{cc}2"], (max, "RobustMpc", 1) ),
            (["dynamic", f"{cc}1", f"{cc}2"], (max, "Dynamic", 1) ),
        
            # fairness
            (["versus", "robustMpc", f"{cc}", "gap2"], ("robustMpc", "Gap-RobustMpc", 2) ),
            (["versus", "dynamic", f"{cc}", "gap2"], ("robustMpc", "Gap-Dynamic", 2) ),
            (["rmpc", f"{cc}1", f"{cc}2"], (min, "RobustMpc", 2) ),
            (["dynamic", f"{cc}1", f"{cc}2"], (min, "Dynamic", 2) ),
        ], metrics=["vmaf_qoe"], y_labels={'vmaf_qoe' : 'QoE'}, **kwargs)
   
    def plot_hetero_versus(path: str, experiments: List[Experiment], cc: str, **kwargs) -> None:
        plot_bar(path, experiments, [
            # performance
            (["versus", "robustMpc", f"{cc}", "gap2"], ("abrcc", "Gap-RobustMpc", 1) ),
            (["versus", "dynamic", f"{cc}", "gap2"], ("abrcc", "Gap-Dynamic", 1) ),
            (["rmpc", f"{cc}1", f"{cc}2"], (min, "RobustMpc", 1) ),
            (["dynamic", f"{cc}1", f"{cc}2"], (min, "Dynamic", 1) ),
        
            # fairness
            (["versus", "robustMpc", f"{cc}", "gap2"], ("robustMpc", "Gap-RobustMpc", 2) ),
            (["versus", "dynamic", f"{cc}", "gap2"], ("robustMpc", "Gap-Dynamic", 2) ),
            (["rmpc", f"{cc}1", f"{cc}2"], (max, "RobustMpc", 2) ),
            (["dynamic", f"{cc}1", f"{cc}2"], (max, "Dynamic", 2) ),
        ], metrics=["vmaf_qoe"], y_labels={'vmaf_qoe' : 'QoE'}, **kwargs)

    def plot_self(path: str, experiments: List[Experiment], **kwargs) -> None:
        plot_bar(path, experiments, [
            (["self", "gap", "gap2"], (min, " Gap", 1) ),
            (["dynamic", "cubic1", "cubic2"], (min, "Dynamic-Cubic", 1) ),
            (["dynamic", "bbr21", "bbr22"], (min, "Dynamic-BBR", 1) ),
            (["rmpc", "cubic1", "cubic2"], (min, "RobustMpc-Cubic", 1) ),
            (["rmpc", "bbr21", "bbr22"], (min, "RobustMpc-BBR", 1) ),
            (["minervann"], (min, "Minerva", 1) ),
            
            (["self", "gap", "gap2"], (avg, " Gap", 2) ),
            (["dynamic", "cubic1", "cubic2"], (avg, "Dynamic-Cubic", 2) ),
            (["dynamic", "bbr21", "bbr22"], (avg, "Dynamic-BBR", 2) ),
            (["rmpc", "cubic1", "cubic2"], (avg, "RobustMpc-Cubic", 2) ),
            (["rmpc", "bbr21", "bbr22"], (avg, "RobustMpc-BBR", 2) ),
            (["minervann"], (avg, "Minerva", 2) ),
        ], metrics=["vmaf_qoe"], y_labels={'vmaf_qoe' : 'QoE'}, **kwargs)
    
    def plot_traces(path: str, experiments: List[Experiment]) -> None:
        plot_cdf(path, experiments, [
            (["traces", "rmpc_bbr"], ("robustMpc", "RobustMpc-BBR", 1) ),
            (["traces", "dynamic_bbr"], ("dynamic", "Dynamic-BBR", 1) ),
            (["traces", "dynamic_cubic"], ("dynamic", "Dynamic-Cubic", 1) ),
            (["traces", "rmpc_cubic"], ("robustMpc", "RobustMpc-Cubic", 1) ),
            (["traces", "gap_pid"], ("abrcc", "Gap", 1) ),
        ], metrics=["vmaf", "vmaf_qoe"], x_labels={'vmaf_qoe': 'QoE', 'vmaf': 'VMAF'})

    def plot_fct_traffic(path: str, experiments: List[Experiment], bw: Optional[int] = None) -> None:
        extra = [f"bw{bw}"] if bw else []
        plot_fct_cdf(path, experiments, [
            (["fct", "robustMpc", "bbr2"] + extra, ('abr', "RobustMpc-BBR", 1) ),
            (["fct", "robustMpc", "cubic"] + extra, ('abr', "RobustMpc-Cubic", 1) ),
            (["fct", "dynamic", "bbr2"] + extra, ('abr', "Dynamic-BBR", 1) ),
            (["fct", "dynamic", "cubic"] + extra, ('abr', "Dynamic-Cubic", 1) ),
            (["fct", "gap"] + extra, ('abr', "Gap", 1) ),
        ])

    def plot_flow_capacity(path: str, experiments: List[Experiment]) -> None:
        plot_flow_capacity_cdf(path, experiments, [
            (["sf", "robustMpc", "bbr2"], ('abr', "RobustMpc-BBR", 1) ),
            (["sf", "robustMpc", "cubic"], ('abr', "RobustMpc-Cubic", 1) ),
            (["sf", "dynamic", "bbr2"], ('abr', "Dynamic-BBR", 1) ),
            (["sf", "dynamic", "cubic"], ('abr', "Dynamic-Cubic", 1) ),
            (["sf", "gap"], ('abr', "Gap", 1) ),
        ])
        
        plot_cdf(path, experiments, [
            (["sf", "robustMpc", "bbr2"], ('abr', "RobustMpc-BBR", 1) ),
            (["sf", "robustMpc", "cubic"], ('abr', "RobustMpc-Cubic", 1) ),
            (["sf", "dynamic", "bbr2"], ('abr', "Dynamic-BBR", 1) ),
            (["sf", "dynamic", "cubic"], ('abr', "Dynamic-Cubic", 1) ),
            (["sf", "gap"], ('abr', "Gap", 1) ),
        ], metrics=["vmaf_qoe"], x_labels={'vmaf_qoe': 'QoE'})
    
    def plot_stream_count(path: str, experiments: List[Experiment], partial_tag: str, func_name: str, func, **kwargs) -> None:
        plot_tag(path, experiments, [
            (["robustMpc", "bbr2"], (func, "RobustMpc-BBR", 1) ),
            (["robustMpc", "cubic"], (func, "RobustMpc-Cubic", 1) ),
            (["dynamic", "bbr2"], (func, "Dynamic-BBR", 1) ),
            (["dynamic", "cubic"], (func, "Dynamic-Cubic", 1) ),
            (["gap"], (func, "Gap", 1) ),
            (["minervann"], (func, "Minerva", 1) ),
        ], partial_tag, metrics=['vmaf_qoe'], y_labels={'vmaf_qoe': func_name}, **kwargs)

    experiment_path = str(Path("experiments") / "plots")
    os.system(f"mkdir -p {experiment_path}")

    # traffic fct
    traffic_path = str(Path(experiment_path) / "traffic")
    os.system(f"mkdir -p {traffic_path}")
    experiments = sum([load_experiments(experiment) for experiment in [
        str(Path("experiments") / "traffic" / "fct"),
    ]], [])
    for bw in [5, 4, 3]:
        plot_fct_traffic(str(Path(traffic_path) / f"fct{bw}"), experiments, bw=bw)
    plot_fct_traffic(str(Path(traffic_path) / "fct"), experiments)
    
    # single flow traffic
    experiments = sum([load_experiments(experiment) for experiment in [
        str(Path("experiments") / "traffic" / "sft"),
    ]], [])
    plot_flow_capacity(str(Path(traffic_path) / "sft"), experiments)

    # per-video plots
    videos = ['got', 'bojack', 'guard', 'cook']
    for video in videos:
        experiments = sum([load_experiments(experiment) for experiment in [
            str(Path("experiments") / "multiple_videos" / video),
        ]], [])
    
        os.system(f"mkdir -p {experiment_path}/{video}")
        for cc in ['cubic', 'bbr2']:
            plot_versus(str(Path(experiment_path) / video / f"{cc}"), experiments, cc)
        plot_self(str(Path(experiment_path) / video / "self"), experiments)
        plot_traces(str(Path(experiment_path) / video / "traces"), experiments)

    # 3 flow experiments
    for video in videos:
        experiments = sum([load_experiments(experiment) for experiment in [
            str(Path("experiments") / "multiple_videos2" / video),
        ]], [])
    
        os.system(f"mkdir -p {experiment_path}/{video}")
        for cc in ['cubic', 'bbr2']:
            plot_multiple(str(Path(experiment_path) / video / f"multiple_{cc}"), experiments, cc)

    # hetero experiments
    videos = ['got', 'bojack', 'guard']
    for i, video1 in enumerate(videos):
        for j, video2 in enumerate(videos):
            if i != j:
                experiments = sum([load_experiments(experiment) for experiment in [
                    str(Path("experiments") / "hetero" / f"{video1}_{video2}"),
                ]], [])
        
                os.system(f"mkdir -p {experiment_path}/{video1}_{video2}")
                for cc in ['cubic', 'bbr2']:
                    plot_hetero_versus(str(Path(experiment_path) / f"{video1}_{video2}" / f"{cc}"), experiments, cc)
                plot_self(str(Path(experiment_path) / f"{video1}_{video2}" / "self"), experiments)

    # stream count    
    stream_count_path = str(Path(experiment_path) / "stream_count")
    os.system(f"mkdir -p {stream_count_path}")
    experiments = sum([load_experiments(experiment) for experiment in [
        str(Path("experiments") / "stream_count"),
    ]], [])
    plot_stream_count(
        str(Path(stream_count_path) / "stream_count"), experiments, "streams", 'Total QoE', sum, legend_location=2,
    )
    plot_stream_count(
        str(Path(stream_count_path) / "stream_count_fair"), experiments, "streams", 'Minimum QoE', min, legend_location=1,
    )
    plot_stream_count(
        str(Path(stream_count_path) / "stream_count_cv"), experiments, "streams", 'QoE CV', cv, legend_location=2,
    )

    # summaries
    videos = ['got', 'bojack', 'guard', 'cook']
    experiments = sum([load_experiments(experiment) for experiment in [
        str(Path("experiments") / "multiple_videos" / video)
        for video in videos
    ]], [])
    experiments2 = sum([load_experiments(experiment) for experiment in [
        str(Path("experiments") / "multiple_videos" / video)
        for video in ['guard', 'bojack', 'cook']
    ]], [])
    os.system(f"mkdir -p {experiment_path}/summary")
    for cc in ['cubic', 'bbr2']:
        plot_versus(str(Path(experiment_path) / 'summary' / f"{cc}"), experiments, cc)
    plot_self(str(Path(experiment_path) / 'summary' / "self"), experiments)
    plot_traces(str(Path(experiment_path) / 'summary' / "traces"), experiments2)
    
    # summary multiple
    experiments = sum([load_experiments(experiment) for experiment in [
        str(Path("experiments") / "multiple_videos2" / video)
        for video in videos
    ]], [])
    for cc in ['cubic', 'bbr2']:
        plot_multiple(str(Path(experiment_path) / "summary" / f"multiple_{cc}"), experiments, cc)

    # summary hetero
    experiments = []
    videos = ['got', 'bojack', 'guard']
    for i, video1 in enumerate(videos):
        for j, video2 in enumerate(videos):
            if j > i:
                experiments += sum([load_experiments(experiment) for experiment in [
                    str(Path("experiments") / "hetero" / f"{video1}_{video2}"),
                ]], [])
    for cc in ['cubic', 'bbr2']:
        plot_hetero_versus(str(Path(experiment_path) / f"summary" / f"hetero_{cc}"), experiments, cc)
    plot_self(str(Path(experiment_path) / f"summary" / "hetero_self"), experiments, exclude=[], legend_location=3)


@experiment
def run_all(args: Namespace) -> None:
    traffic(args)
    multiple(args)
    multiple2(args)
    hetero(args) 
    single_flow_traffic(args)
    stream_count(args) 


if __name__ == "__main__":
    parser = ArgumentParser(description=
        f'Run experiment setup in this Python file. ' +
        f'Available experiments: {list(experiments().keys())}')
    parser.add_argument('name', type=str, help='Experiment name.')
    parser.add_argument('-d', '--dry', action='store_true', dest='dry', help='Dry run.')
    parser.add_argument('-hl', '--headless', action='store_true', dest='headless', help='Hide the UI.')
    args = parser.parse_args()

    if args.name in experiments():
        experiments()[args.name](args)
    else:
        print(f'No such experiment: {args.name}')
        print(f'Available experiments: {list(EXPERIMENTS.keys())}')
