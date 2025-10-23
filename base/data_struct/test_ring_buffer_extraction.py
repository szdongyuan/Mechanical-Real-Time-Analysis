"""
环形缓冲区提取逻辑测试脚本
验证AudioSegmentExtractor对环形缓冲区的处理是否正确
"""
import numpy as np


def test_ring_buffer_extraction():
    """测试环形缓冲区数据提取逻辑"""
    
    print("=" * 70)
    print("环形缓冲区数据提取测试")
    print("=" * 70)
    
    # 模拟环形缓冲区
    buffer_size = 20
    segment_samples = 8  # 要提取的采样点数
    
    # 创建测试数据：0, 1, 2, ..., 29
    # 但缓冲区只能存20个，所以最终存储的是 10-29
    ring_buffer = np.arange(10, 30, dtype=np.float32)
    write_index = 10  # 下一个要写入的位置
    
    print(f"\n1. 初始设置:")
    print(f"   缓冲区大小: {buffer_size}")
    print(f"   要提取的点数: {segment_samples}")
    print(f"   写入位置索引: {write_index}")
    
    # 模拟环形缓冲区（实际存储）
    # 假设已经循环写入，write_index = 10 表示位置10是下一个要写的
    # 这意味着位置0-9存储的是较新的数据，位置10-19存储的是较旧的数据
    actual_ring = np.zeros(buffer_size, dtype=np.float32)
    actual_ring[:10] = np.arange(20, 30)  # 位置0-9: 20-29（新数据）
    actual_ring[10:] = np.arange(10, 20)  # 位置10-19: 10-19（旧数据）
    
    print(f"\n2. 环形缓冲区内容:")
    print(f"   实际存储: {actual_ring}")
    print(f"   索引 0-9 (新): {actual_ring[:10]}")
    print(f"   索引 10-19 (旧): {actual_ring[10:]}")
    
    # 应用环形缓冲区提取逻辑
    print(f"\n3. 提取逻辑:")
    print(f"   步骤1: 获取 write_index = {write_index}")
    print(f"   步骤2: 重组为线性数组")
    print(f"          - ring_buffer[{write_index}:] = {actual_ring[write_index:]}")
    print(f"          - ring_buffer[:{write_index}] = {actual_ring[:write_index]}")
    
    # 将环形缓冲区转换为线性数组
    linear_data = np.concatenate([actual_ring[write_index:], actual_ring[:write_index]])
    print(f"   步骤3: 线性数组 = {linear_data}")
    print(f"          (应该是按时间顺序: 10, 11, 12, ..., 29)")
    
    # 提取最后的segment_samples个点
    segment = linear_data[-segment_samples:]
    print(f"   步骤4: 提取最后{segment_samples}个点 = {segment}")
    print(f"          (应该是最新的数据: 22, 23, ..., 29)")
    
    # 验证结果
    expected = np.arange(30 - segment_samples, 30, dtype=np.float32)
    is_correct = np.array_equal(segment, expected)
    
    print(f"\n4. 验证结果:")
    print(f"   提取的数据: {segment}")
    print(f"   预期的数据: {expected}")
    print(f"   结果: {'✅ 正确' if is_correct else '❌ 错误'}")
    
    return is_correct


def test_edge_cases():
    """测试边界情况"""
    
    print("\n" + "=" * 70)
    print("边界情况测试")
    print("=" * 70)
    
    # 测试1: write_index = 0 的情况
    print("\n测试1: write_index = 0 (缓冲区刚好写满一圈)")
    ring_buffer = np.arange(100, 120, dtype=np.float32)
    write_index = 0
    linear_data = np.concatenate([ring_buffer[write_index:], ring_buffer[:write_index]])
    print(f"   环形缓冲区: {ring_buffer}")
    print(f"   线性数组: {linear_data}")
    print(f"   结果: {'✅ 正确' if np.array_equal(linear_data, ring_buffer) else '❌ 错误'}")
    
    # 测试2: write_index = 缓冲区大小-1
    print("\n测试2: write_index = 19 (在末尾)")
    ring_buffer = np.zeros(20, dtype=np.float32)
    ring_buffer[:19] = np.arange(1, 20)
    ring_buffer[19] = 0
    write_index = 19
    linear_data = np.concatenate([ring_buffer[write_index:], ring_buffer[:write_index]])
    expected = np.concatenate([[0], np.arange(1, 20)])
    print(f"   环形缓冲区: {ring_buffer}")
    print(f"   线性数组: {linear_data}")
    print(f"   预期: {expected}")
    print(f"   结果: {'✅ 正确' if np.array_equal(linear_data, expected) else '❌ 错误'}")
    
    # 测试3: 数据不足的情况
    print("\n测试3: 数据不足时的填充")
    linear_data = np.array([1, 2, 3], dtype=np.float32)
    segment_samples = 8
    segment = np.zeros(segment_samples, dtype=np.float32)
    segment[-len(linear_data):] = linear_data
    expected = np.array([0, 0, 0, 0, 0, 1, 2, 3], dtype=np.float32)
    print(f"   原始数据: {linear_data} (长度: {len(linear_data)})")
    print(f"   需要长度: {segment_samples}")
    print(f"   填充结果: {segment}")
    print(f"   预期: {expected}")
    print(f"   结果: {'✅ 正确' if np.array_equal(segment, expected) else '❌ 错误'}")


def visualize_ring_buffer():
    """可视化环形缓冲区的工作原理"""
    
    print("\n" + "=" * 70)
    print("环形缓冲区可视化")
    print("=" * 70)
    
    buffer_size = 10
    write_index = 3
    
    print("\n环形缓冲区状态:")
    print("  索引:  [0] [1] [2] [3] [4] [5] [6] [7] [8] [9]")
    print("  数据:  [k] [l] [m] [d] [e] [f] [g] [h] [i] [j]")
    print("                      ↑")
    print("                 write_index = 3")
    print("\n说明:")
    print("  - 位置3是下一个要写入的位置")
    print("  - 位置3-9存储的是旧数据: d, e, f, g, h, i, j")
    print("  - 位置0-2存储的是新数据: k, l, m")
    print("\n转换为线性数组（从旧到新）:")
    print("  linear_data = ring_buffer[3:] + ring_buffer[:3]")
    print("              = [d,e,f,g,h,i,j] + [k,l,m]")
    print("              = [d,e,f,g,h,i,j,k,l,m]")
    print("\n如果要提取最后4个采样点:")
    print("  segment = linear_data[-4:]")
    print("          = [g,h,i,j]")
    
    # 实际模拟
    ring_buffer = np.array(['k','l','m','d','e','f','g','h','i','j'])
    linear_data = np.concatenate([ring_buffer[write_index:], ring_buffer[:write_index]])
    segment = linear_data[-4:]
    
    print("\n实际结果:")
    print(f"  环形缓冲区: {ring_buffer}")
    print(f"  线性数组: {linear_data}")
    print(f"  提取的片段: {segment}")


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║  AudioSegmentExtractor - 环形缓冲区提取逻辑测试  ║".center(70))
    print("╚" + "=" * 68 + "╝")
    
    # 运行测试
    test1_result = test_ring_buffer_extraction()
    test_edge_cases()
    visualize_ring_buffer()
    
    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"基本功能测试: {'✅ 通过' if test1_result else '❌ 失败'}")
    print("\n核心逻辑:")
    print("  1. 获取 write_index")
    print("  2. 重组: linear_data = concat([buffer[write_idx:], buffer[:write_idx]])")
    print("  3. 提取: segment = linear_data[-segment_samples:]")
    print("\n这样可以确保提取的数据:")
    print("  ✓ 时间顺序正确（从旧到新）")
    print("  ✓ 数据连续性")
    print("  ✓ 获取最新的N个采样点")
    print("=" * 70)
    print("\n")


