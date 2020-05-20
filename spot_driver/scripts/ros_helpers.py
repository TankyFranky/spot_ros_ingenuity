import rospy

from tf2_msgs.msg import TFMessage
from geometry_msgs.msg import TransformStamped
from sensor_msgs.msg import Image, CameraInfo
from sensor_msgs.msg import JointState
from geometry_msgs.msg import TwistWithCovarianceStamped

friendly_joint_names = {}
"""Dictionary for mapping BD joint names to more friendly names"""
friendly_joint_names["fl.hx"] = "front_left_hip_x"
friendly_joint_names["fl.hy"] = "front_left_hip_y"
friendly_joint_names["fl.kn"] = "front_left_knee"
friendly_joint_names["fr.hx"] = "front_right_hip_x"
friendly_joint_names["fr.hy"] = "front_right_hip_y"
friendly_joint_names["fr.kn"] = "front_right_knee"
friendly_joint_names["hl.hx"] = "rear_left_hip_x"
friendly_joint_names["hl.hy"] = "rear_left_hip_y"
friendly_joint_names["hl.kn"] = "rear_left_knee"
friendly_joint_names["hr.hx"] = "rear_right_hip_x"
friendly_joint_names["hr.hy"] = "rear_right_hip_y"
friendly_joint_names["hr.kn"] = "rear_right_knee"

class DefaultCameraInfo(CameraInfo):
    def __init__(self):
        super().__init__()
        self.distortion_model = "plumb_bob"

        self.D.append(0)
        self.D.append(0)
        self.D.append(0)
        self.D.append(0)
        self.D.append(0)

        self.K[1] = 0
        self.K[3] = 0
        self.K[6] = 0
        self.K[7] = 0
        self.K[8] = 1

        self.R[0] = 1
        self.R[1] = 0
        self.R[2] = 0
        self.R[3] = 0
        self.R[4] = 1
        self.R[5] = 0
        self.R[6] = 0
        self.R[7] = 0
        self.R[8] = 1

        self.P[1] = 0
        self.P[3] = 0
        self.P[4] = 0
        self.P[7] = 0
        self.P[8] = 0
        self.P[9] = 0
        self.P[10] = 1
        self.P[11] = 0

def getImageMsg(data):
    """Maps image data from image proto to ROS image message

    Args:
        data: Image proto
    """
    tf_msg = TFMessage()
    for frame_name in data.shot.transforms_snapshot.child_to_parent_edge_map:
        if data.shot.transforms_snapshot.child_to_parent_edge_map.get(frame_name).parent_frame_name:
            transform = data.shot.transforms_snapshot.child_to_parent_edge_map.get(frame_name)
            new_tf = TransformStamped()
            new_tf.header.stamp = rospy.Time(data.shot.acquisition_time.seconds, data.shot.acquisition_time.nanos)
            new_tf.header.frame_id = transform.parent_frame_name
            new_tf.child_frame_id = frame_name
            new_tf.transform.translation.x = transform.parent_tform_child.position.x
            new_tf.transform.translation.y = transform.parent_tform_child.position.y
            new_tf.transform.translation.z = transform.parent_tform_child.position.z
            new_tf.transform.rotation.x = transform.parent_tform_child.rotation.x
            new_tf.transform.rotation.y = transform.parent_tform_child.rotation.y
            new_tf.transform.rotation.z = transform.parent_tform_child.rotation.z
            new_tf.transform.rotation.w = transform.parent_tform_child.rotation.w
            tf_msg.transforms.append(new_tf)

    image_msg = Image()
    image_msg.header.stamp = rospy.Time(data.shot.acquisition_time.seconds, data.shot.acquisition_time.nanos)
    image_msg.header.frame_id = data.shot.frame_name_image_sensor
    image_msg.height = data.shot.image.rows
    image_msg.width = data.shot.image.cols

    # Color/greyscale formats.
    # JPEG format
    if data.shot.image.format == 1:
        image_msg.encoding = "rgb8"
        image_msg.is_bigendian = True
        image_msg.step = 3 * data.shot.image.cols
        image_msg.data = data.shot.image.data

    # Uncompressed.  Requires pixel_format.
    if data.shot.image.format == 2:
        # One byte per pixel.
        if data.shot.image.pixel_format == 1:
            image_msg.encoding = "mono8"
            image_msg.is_bigendian = True
            image_msg.step = data.shot.image.cols
            image_msg.data = data.shot.image.data

        # Three bytes per pixel.
        if data.shot.image.pixel_format == 3:
            image_msg.encoding = "rgb8"
            image_msg.is_bigendian = True
            image_msg.step = 3 * data.shot.image.cols
            image_msg.data = data.shot.image.data

        # Four bytes per pixel.
        if data.shot.image.pixel_format == 4:
            image_msg.encoding = "rgba8"
            image_msg.is_bigendian = True
            image_msg.step = 4 * data.shot.image.cols
            image_msg.data = data.shot.image.data

        # Little-endian uint16 z-distance from camera (mm).
        if data.shot.image.pixel_format == 5:
            image_msg.encoding = "mono16"
            image_msg.is_bigendian = False
            image_msg.step = 2 * data.shot.image.cols
            image_msg.data = data.shot.image.data

    camera_info_msg = DefaultCameraInfo()
    camera_info_msg.header.stamp = rospy.Time(data.shot.acquisition_time.seconds, data.shot.acquisition_time.nanos)
    camera_info_msg.header.frame_id = data.shot.frame_name_image_sensor
    camera_info_msg.height = data.shot.image.rows
    camera_info_msg.width = data.shot.image.cols

    camera_info_msg.K[0] = data.source.pinhole.intrinsics.focal_length.x
    camera_info_msg.K[2] = data.source.pinhole.intrinsics.principal_point.x
    camera_info_msg.K[4] = data.source.pinhole.intrinsics.focal_length.y
    camera_info_msg.K[5] = data.source.pinhole.intrinsics.principal_point.y

    camera_info_msg.P[0] = data.source.pinhole.intrinsics.focal_length.x
    camera_info_msg.P[2] = data.source.pinhole.intrinsics.principal_point.x
    camera_info_msg.P[5] = data.source.pinhole.intrinsics.focal_length.y
    camera_info_msg.P[6] = data.source.pinhole.intrinsics.principal_point.y

    return image_msg, camera_info_msg, tf_msg

def GetJointStatesFromState(state):
    joint_state = JointState()
    joint_state.header.stamp = rospy.Time(state.kinematic_state.acquisition_timestamp.seconds, state.kinematic_state.acquisition_timestamp.nanos)
    for joint in state.kinematic_state.joint_states:
        joint_state.name.append(friendly_joint_names.get(joint.name, "ERROR"))
        joint_state.position.append(joint.position.value)
        joint_state.velocity.append(joint.velocity.value)
        joint_state.effort.append(joint.load.value)

    return joint_state

def GetEStopStateFromState(state):
    estop_array_msg = EStopStateArray()
    for estop in state.estop_states:
        estop_msg = EStopState()
        estop_msg.header.stamp = rospy.Time(estop.timestamp.seconds, estop.timestamp.nanos)
        estop_msg.name = estop.name
        estop_msg.type = estop.type
        estop_msg.state = estop.state
        estop_array_msg.estop_states.append(estop_msg)

    return estop_array_msg

def GetFeetFromState(state):
    foot_array_msg = FootStateArray()
    for foot in state.foot_state:
        foot_msg = FootState()
        foot_msg.foot_position_rt_body.x = foot.foot_position_rt_body.x
        foot_msg.foot_position_rt_body.y = foot.foot_position_rt_body.y
        foot_msg.foot_position_rt_body.z = foot.foot_position_rt_body.z
        foot_msg.contact = foot.contact
        foot_array_msg.states.append(foot_msg)

    return foot_array_msg

def GetOdomTwistFromState(state):
    twist_odom_msg = TwistWithCovarianceStamped()
    twist_odom_msg.header.stamp = rospy.Time(state.kinematic_state.acquisition_timestamp.seconds, state.kinematic_state.acquisition_timestamp.nanos)
    twist_odom_msg.twist.twist.linear.x = state.kinematic_state.velocity_of_body_in_odom.linear.x
    twist_odom_msg.twist.twist.linear.y = state.kinematic_state.velocity_of_body_in_odom.linear.y
    twist_odom_msg.twist.twist.linear.z = state.kinematic_state.velocity_of_body_in_odom.linear.z
    twist_odom_msg.twist.twist.angular.x = state.kinematic_state.velocity_of_body_in_odom.angular.x
    twist_odom_msg.twist.twist.angular.y = state.kinematic_state.velocity_of_body_in_odom.angular.y
    twist_odom_msg.twist.twist.angular.z = state.kinematic_state.velocity_of_body_in_odom.angular.z
    return twist_odom_msg

def GetWifiFromState(state):
    wifi_msg = WiFiState()
    for comm_state in state.comms_states:
        if comm_state.HasField('wifi_state'):
            wifi_msg.current_mode = comm_state.wifi_state.current_mode
            wifi_msg.essid = comm_state.wifi_state.essid

    return wifi_msg

def GetTFFromState(state):
    tf_msg = TFMessage()
    for frame_name in state.kinematic_state.transforms_snapshot.child_to_parent_edge_map:
        if state.kinematic_state.transforms_snapshot.child_to_parent_edge_map.get(frame_name).parent_frame_name:
            transform = state.kinematic_state.transforms_snapshot.child_to_parent_edge_map.get(frame_name)
            new_tf = TransformStamped()
            new_tf.header.stamp = rospy.Time(state.kinematic_state.acquisition_timestamp.seconds, state.kinematic_state.acquisition_timestamp.nanos)
            new_tf.header.frame_id = transform.parent_frame_name
            new_tf.child_frame_id = frame_name
            new_tf.transform.translation.x = transform.parent_tform_child.position.x
            new_tf.transform.translation.y = transform.parent_tform_child.position.y
            new_tf.transform.translation.z = transform.parent_tform_child.position.z
            new_tf.transform.rotation.x = transform.parent_tform_child.rotation.x
            new_tf.transform.rotation.y = transform.parent_tform_child.rotation.y
            new_tf.transform.rotation.z = transform.parent_tform_child.rotation.z
            new_tf.transform.rotation.w = transform.parent_tform_child.rotation.w
            tf_msg.transforms.append(new_tf)

    return tf_msg

def GetBatteryStatesFromState(state):
    battery_states_array_msg = BatteryStateArray()
    for battery in state.battery_states:
        battery_msg = BatteryState()
        battery_msg.header.stamp = rospy.Time(battery.timestamp.seconds, battery.timestamp.nanos)

        battery_msg.identifier = battery.identifier
        battery_msg.charge_percentage = battery.charge_percentage.value
        battery_msg.estimated_runtime = rospy.Time(battery.estimated_runtime.seconds, battery.estimated_runtime.nanos)
        battery_msg.current = battery.current.value
        battery_msg.voltage = battery.voltage.value
        for temp in battery.temperatures:
            battery_msg.temperatures.append(temp)
        battery_msg.status = battery.status
        battery_states_array_msg.battery_states.append(battery_msg)

    return battery_states_array_msg

def GetPowerStatesFromState(state):
    power_state_msg = PowerState()
    power_state_msg.header.stamp = rospy.Time(state.power_state.timestamp.seconds, state.power_state.timestamp.nanos)
    power_state_msg.motor_power_state = state.power_state.motor_power_state
    power_state_msg.shore_power_state = state.power_state.shore_power_state
    power_state_msg.locomotion_charge_percentage = state.power_state.locomotion_charge_percentage.value
    power_state_msg.locomotion_estimated_runtime = rospy.Time(state.power_state.locomotion_estimated_runtime.seconds, state.power_state.locomotion_estimated_runtime.nanos)
    return power_state_msg

    def getBehaviorFaults(behavior_faults):
        """Helper function to strip out behavior faults into a list

        Args:
            behavior_faults: List of BehaviorFaults
        """
        faults = []

        for fault in behavior_faults:
            new_fault = BehaviorFault()
            new_fault.behavior_fault_id = fault.behavior_fault_id
            new_fault.header.stamp = rospy.Time(fault.onset_timestamp.seconds, fault.onset_timestamp.nanos)
            new_fault.cause = fault.cause
            new_fault.status = fault.status
            faults.append(new_fault)

        return faults

    def getSystemFaults(system_faults):
        """Helper function to strip out system faults into a list

        Args:
            systen_faults: List of SystemFaults
        """
        faults = []

        for fault in system_faults:
            new_fault = SystemFault()
            new_fault.name = fault.name
            new_fault.header.stamp = rospy.Time(fault.onset_timestamp.seconds, fault.onset_timestamp.nanos)
            new_fault.duration = rospy.Time(fault.duration.seconds, fault.duration.nanos)
            new_fault.code = fault.code
            new_fault.uid = fault.uid
            new_fault.error_message = fault.error_message

            for att in fault.attributes:
                new_fault.attributes.append(att)

            new_fault.severity = fault.severity
            faults.append(new_fault)

        return faults

def GetSystemFaultsFromState(state):
    system_fault_state_msg = SystemFaultState()
    system_fault_state_msg.faults = getSystemFaults(state.system_fault_state.faults)
    system_fault_state_msg.historical_faults = getSystemFaults(state.system_fault_state.historical_faults)
    return system_fault_state_msg

def getBehaviorFaultsFromState(state):
    behavior_fault_state_msg = BehaviorFaultState()
    behavior_fault_state_msg.faults = getBehaviorFaults(state.behavior_fault_state.faults)
    return behavior_fault_state_msg