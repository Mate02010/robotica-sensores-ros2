"""Camara real OpenNI2, profundidad original/filtrada y nubes XYZ sin registro RGB."""
from pathlib import Path
import sys
import yaml
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode


def generate_launch_description():
    base = Path(__file__).resolve().parent
    params = yaml.safe_load((base / 'config/driver.yaml').read_text())['/camera/driver']['ros__parameters']
    nodos = [ComposableNode(package='openni2_camera', plugin='openni2_wrapper::OpenNI2Driver',
                             name='driver', namespace='camera', parameters=[params])]
    for nombre, imagen, nube in [('puntos_originales', '/camera/depth_raw/image', '/camera/depth/points'),
                                 ('puntos_filtrados', '/camera/depth_filtrada/image_raw', '/camera/depth_filtrada/points')]:
        nodos.append(ComposableNode(package='depth_image_proc', plugin='depth_image_proc::PointCloudXyzNode',
                                   name=nombre, namespace='camera',
                                   remappings=[('image_rect', imagen),
                                               ('camera_info', '/camera/depth_raw/camera_info'), ('points', nube)]))
    return LaunchDescription([
        ComposableNodeContainer(name='container', namespace='camera', package='rclcpp_components',
                                executable='component_container', composable_node_descriptions=nodos, output='screen'),
        ExecuteProcess(cmd=[sys.executable, '-u', str(base / 'filtro_profundidad.py'), '--ros-args',
                            '--params-file', str(base / 'config/filtros.yaml')], output='screen'),
        # Misma posicion del sensor; solo cambia convencion optica a ejes ROS.
        Node(package='tf2_ros', executable='static_transform_publisher', arguments=[
            '--frame-id', 'camera_link', '--child-frame-id', 'camera_depth_optical_frame',
            '--roll', '-1.5707963267948966', '--yaw', '-1.5707963267948966'], output='screen'),
    ])
