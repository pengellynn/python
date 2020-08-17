import wntr
import pickle
import numpy as np
import random
import queue

inp_file = r'C:\Users\29040\Desktop\data\ky7 EPANET\ky7.inp'
output_file = r'C:\Users\29040\Desktop\ky7.txt'

failure_pipe_set = set()
failure_segment_set = set()


def simulate():
    # 创建水网络模型
    wn = wntr.network.WaterNetworkModel(inp_file)
    # 快照原始水网络模型
    pickle_network(wn, 'wn0.pickle')

    # 随机生成一些阀门
    index = random.sample(range(0, wn.num_pipes), 100)
    for i in range(100):
        pn = wn.pipe_name_list[index[i]]
        pipe = wn.get_link(pn)
        vn = 'valve_'+str(pn)
        wn.add_valve(vn, pipe.start_node_name, pipe.end_node_name, pipe.diameter, 'FCV')
        valve = wn.get_link(vn)
        valve.status = 1
    
    # 快照增加阀门后的水网络模型
    pickle_network(wn, 'wn1.pickle')

    # 识别segment
    link_dict = {}
    node_dict = {}
    valve_dict0 = {}
    valve_dict1 = {}
    for name in wn.link_name_list:
        link = wn.get_link(name)
        if link.link_type == 'Valve':
            valve_dict0.update({name: 0})
            valve_dict1.update({name: 0})
        else:
            link_dict.update({name: 0})
    for name in wn.node_name_list:
        node_dict.update({name: 0})
    m = 0
    q = queue.Queue()
    for ln in wn.link_name_list:
        link = wn.get_link(ln)
        if link.link_type == 'Valve':
            continue
        if link_dict[ln] == 0:
            m = m + 1
            link_dict.update({ln: m})
            link = wn.get_link(ln)
            q.put(link.start_node_name)
            q.put(link.end_node_name)
            while not q.empty():
                node = q.get()
                if node_dict[node] == 0:
                    node_dict.update({node: m})
                links = wn.get_links_for_node(node)
                if links is not None or len(links) != 0:
                    for l in links:
                        # 管段存在阀门时跳过
                        if 'valve_' + l in links:
                            if link_dict[l] == 0:
                                link_dict[l] = m
                            continue
                        link = wn.get_link(l)
                        if link.link_type == 'Valve':
                            if valve_dict0[link.name] == 0:
                                valve_dict0.update({link.name: m})
                            else:
                                valve_dict1.update({link.name: m})
                        else:
                            if link_dict[link.name] == 0:
                                link_dict.update({link.name: m})
                                if link.end_node_name != node:
                                    q.put(link.end_node_name)
                                else:
                                    q.put(link.start_node_name)

    segment_pipe_list = [[] for i in range(m)]
    for key, value in link_dict.items():
        if value != 0:
            segment_pipe_list[value - 1].append(key)

    segment_valve_list = [[] for i in range(m)]
    for key, value in valve_dict0.items():
        if value != 0:
            segment_valve_list[value - 1].append(key)
    for key, value in valve_dict1.items():
        if value != 0:
            segment_valve_list[value - 1].append(key)

    num_segment = m

    print('segment_pipe_list', segment_pipe_list)
    print('segment_valve_list', segment_valve_list)

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
    wn = reload_network('wn1.pickle')

    pressures = np.array(pressure_list.values)

    # 不同起始时刻进行级联模拟
    for i in range(10,11):
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
            close_valves_and_simulate(wn, node_dict, segment_pipe_list, segment_valve_list, segments, begin_time, level)


# 关闭相应管道后进行水力模拟
def close_valves_and_simulate(wn, node_dict, segment_pipe_list, segment_valve_list, segments, begin_time, level):
    # 没有新的segment失效，级联模拟结束
    if segments is None or len(segments) == 0:
        return
    # 级数递增
    level = level + 1
    print('level', level - 1)
    # 关闭所有新增失效segment
    for s in segments:
        for v in segment_valve_list[s]:
            valve = wn.get_link(v)
            if valve.status != 0:
                valve.status = 0
        print('close valves: ', segment_valve_list[s])
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
                seg = node_dict[node_name]
                if seg not in failure_segment_set:
                    new_failure_segments.add(seg)
                    pipe_name_list = segment_pipe_list[seg]
                    for pipe in pipe_name_list:
                        if pipe not in failure_pipe_set:
                            failure_pipe_set.add(pipe)
                            new_failure_pipes.add(pipe)
        write_failure_components(new_failure_nodes, list(new_failure_pipes), level)
        close_valves_and_simulate(wn, node_dict, segment_pipe_list, segment_valve_list, new_failure_segments, begin_time,
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
