import wntr
import pickle
import numpy as np
import random
import queue

inp_file = r'C:\Users\29040\Desktop\WNTR-master\examples\networks\Net3.inp'
output_file = r'C:\Users\29040\Desktop\Net3.txt'

failure_pipe_set = set()
failure_segment_set = set()


def simulate():
    # 创建水网络模型
    wn = wntr.network.WaterNetworkModel(inp_file)
    # 快照原始水网络模型
    pickle_network(wn, 'wn0.pickle')

    g = wn.get_graph()
    valve_layer = wntr.network.layer.generate_valve_layer(wn, 'random', 50)
    # print(valve_layer)
    node_segments, link_segments, segment_size = wntr.metrics.topographic.valve_segments(g, valve_layer)
    print('node_segments', node_segments)
    print('link_segment', link_segments)
    print('segment_size', segment_size)
    num_segment = len(segment_size)
    segment_pipe_list = [[] for i in range(num_segment)]
    for link in link_segments.index:
        seg = link_segments[link]
        segment_pipe_list[seg].append(link)

    segment_node_list = [[] for i in range(num_segment)]
    for node in node_segments.index:
        seg = node_segments[node]
        segment_node_list[seg].append(node)

    # 设置DD模式下的水力模拟时间参数
    wn.options.time.duration = 24 * 3600
    wn.options.time.hydraulic_timestep = 3600
    wn.options.time.report_timestep = 3600
    # 需求驱动水力模拟，获取节点服务水压
    sim = wntr.sim.WNTRSimulator(wn, 'DD')
    results = sim.run_sim()
    pressure_list = results.node['pressure'].loc[:, wn.junction_name_list]

    print('24小时模拟：')
    print(pressure_list.columns)
    print(pressure_list.values)
    print('================================================')

    # 重新加载水网络模型
    wn = reload_network('wn0.pickle')

    pressures = np.array(pressure_list.values)

    # 不同起始时刻进行级联模拟
    for i in range(10, 13):
        print('pressures length', len(pressures))
        # Set minimum pressures, nominal pressures and max_pressure 
        for j in range(wn.num_junctions):
            print('pressures[i] length', len(pressures[i]))
            node = wn.get_node(wn.junction_name_list[j])
            node.max_pressure = pressures.max(axis=0)[j] * 1.1
            node.nominal_pressure = pressures[i][j]
            node.minimum_pressure = pressures.min(axis=0)[j] * 0.9
            print('节点', wn.junction_name_list[j], node.minimum_pressure, node.nominal_pressure, node.max_pressure)
        print('================================================')
        # 快照设置最小水压、节点服务水压和最大水压后的水网络模型
        pickle_network(wn, 'wn.pickle')
        out = open(output_file, 'a')
        out.write('时刻 ' + str(i) + ':\n')
        out.close()

        level = 0
        begin_time = i * 3600
        # 逐个segment模拟
        for k in range(num_segment):
            # 每次都重新加载水网络模型
            wn = reload_network('wn.pickle')
            failure_pipe_set.clear()
            failure_segment_set.clear()
            # 先模拟至指定时刻
            wn.options.time.duration = begin_time
            sim = wntr.sim.WNTRSimulator(wn, 'PDD')
            sim.run_sim()
            segments = list()
            segments.append(k)
            out = open(output_file, 'a')
            out.write('level 0: close segment ' + str(k) + '\n')
            out.write('level 0: close pipe ')
            for p in range(len(segment_pipe_list[k])):
                if p != 0:
                    out.write(',')
                out.write(segment_pipe_list[k][p])
            out.write('\n')
            out.close()
            close_valves_and_simulate(wn, node_segments, segment_pipe_list, segments, begin_time, level)


# 关闭相应管道后进行水力模拟
def close_valves_and_simulate(wn, node_segments, segment_pipe_list, segments, begin_time, level):
    # 没有新的segment失效，级联模拟结束
    if segments is None or len(segments) == 0:
        return
    # 级数递增
    level = level + 1
    print('level', level - 1)
    # 关闭所有新增失效segment
    for s in segments:
        for p in segment_pipe_list[s]:
            pipe = wn.get_link(p)
            if pipe.status != 0:
                pipe.status = 0
        print('close pipes: ', segment_pipe_list[s])
    # 关闭新增失效segment的阀门后继续模拟一个时段
    wn.options.time.duration = begin_time + level * 3600
    sim = wntr.sim.WNTRSimulator(wn, 'PDD')
    results = sim.run_sim()
    pressure_list = results.node['pressure'].loc[:, wn.junction_name_list]
    print('pressures: ', pressure_list.values[0])
    print('============================================')

    if pressure_list.empty is False:
        new_failure_nodes = list()
        new_failure_pipes = set()
        new_failure_segments = set()
        for i in range(len(pressure_list.values[0])):
            node_name = wn.junction_name_list[i]
            max_pressure = wn.get_node(node_name).max_pressure
            if pressure_list.values[0][i] > max_pressure:
                new_failure_nodes.append(node_name)
                seg = node_segments[node_name]
                if seg not in failure_segment_set:
                    new_failure_segments.add(seg)
                    pipe_name_list = segment_pipe_list[seg]
                    for pipe in pipe_name_list:
                        if pipe not in failure_pipe_set:
                            failure_pipe_set.add(pipe)
                            new_failure_pipes.add(pipe)
        write_failure_components(new_failure_nodes, list(new_failure_pipes), level)
        close_valves_and_simulate(wn, node_segments, segment_pipe_list, new_failure_segments, begin_time,
                                  level)
    else:
        out = open(output_file, 'a')
        out.write('network has crashed!\n')
        out.close()


def write_failure_components(failure_nodes, failure_pipes, level):
    if failure_nodes is None or len(failure_nodes) == 0:
        return
    if failure_pipes is None or len(failure_pipes) == 0:
        return
    out = open(output_file, 'a')
    out.write('level: ' + str(level) + '\n')
    out.write('failure nodes: ')
    for i in range(len(failure_nodes)):
        if i != 0:
            out.write(', ')
        out.write(failure_nodes[i])
    out.write('\n')
    out.write('failure pipes: ')
    for i in range(len(failure_pipes)):
        if i != 0:
            out.write(', ')
        out.write(failure_pipes[i])
    out.write('\n')
    out.close()

# Pickle the network model and reload it for each realization
def pickle_network(wn, file_name):
    f = open(file_name, 'wb')
    pickle.dump(wn, f)
    f.close()


# Reload the water network model
def reload_network(file_name):
    f = open(file_name, 'rb')
    wn = pickle.load(f)
    f.close()
    return wn


if __name__ == "__main__":
    simulate()
