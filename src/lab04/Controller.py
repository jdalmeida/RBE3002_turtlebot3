#!/usr/bin/env python
import rospy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry, Path
from tf.transformations import euler_from_quaternion
from rbe3002.srv import MakePath, RobotNav, FrontierRequest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lab03'))
import map_helper

class Controller:

    def __init__(self):
        """
            This node explores frontiers until no frontiers remain
        """

        # Initialize node
        rospy.init_node('controller', log_level=rospy.DEBUG)

        # Subscribers
        rospy.Subscriber("/odom", Odometry, self.odom_callback)

        # Setup service proxys
        self.make_path = rospy.ServiceProxy('make_path', MakePath)
        self.robot_nav = rospy.ServiceProxy('robot_nav', RobotNav)
        self.frontier_request = rospy.ServiceProxy('get_frontiers', FrontierRequest)

        self.goal = PoseStamped()

        self.pose = None

        rate = rospy.Rate(3000)
        rate.sleep()

        while(self.pose is None):
            rospy.sleep(20)
        self.start_pose = self.pose

        self.state_machine("Explore")

    def odom_callback(self, msg):
        # type: (Odometry) -> None
        """
        update the state of the robot
        :type msg: Odom
        :return:
        """
        position = msg.pose.pose.position
        new_pose = PoseStamped()
        new_pose.pose.position = position
        self.pose = new_pose

    def explore(self):
        rospy.loginfo("Exploring...")
        path_found = False
        done_exploring = False
        path_poses = Path().poses
        
        if self.pose is None:
            rospy.loginfo("No known pose!")
            return

        frontier_request_response = self.frontier_request()
        map = frontier_request_response.map
        frontiers = frontier_request_response.frontiers

        for frontier in frontiers:
            path_response = self.make_path(self.pose, frontier, map)
            # rospy.logdebug("Response: %s" % path_response)
            # rospy.logdebug("Successful path: %s" % path_response.success)
            rospy.loginfo("Potential Path points: ")
            for pose in path_response.path.poses:
                rospy.loginfo(pose.pose.position)
            rospy.loginfo("Potential Horizon Path points: ")
            for pose in path_response.horiz_path.poses:
                rospy.loginfo(pose.pose.position)
            if path_response.success:
                path_found = True
                path_poses = path_response.horiz_path.poses
                #rospy.logdebug("Successful, going to path %s" % path_response.horiz_path.poses)
                break

        if not path_found:
            done_exploring = True
        else:

            rospy.logdebug("Trying to go to a frontier")
            rospy.loginfo("Path points: ")
            for pose in path_response.path.poses:
                rospy.loginfo(pose.pose.position)
            rospy.loginfo("Horizon Path points: ")
            for pose in path_response.horiz_path.poses:
                rospy.loginfo(pose.pose.position)

            for pose in path_poses:
                if not self.robot_nav(pose, True):
                    rospy.logwarn("Robot navigation failed")
                    return
            #     # rospy.logdebug("At point %s" % self.pose)
            # self.robot_nav(path_poses[-1], False)

        if done_exploring:
            rospy.loginfo("Done Exploring")
        return done_exploring

    def state_machine(self, state):
        if(state == "Explore"):
            while not rospy.is_shutdown() and not self.explore():
                pass
            self.save_map()
            state = "Home"
        if(state == "Home"):
            while not rospy.is_shutdown() and not self.home():
                pass
            state = "Travel"
        if(state == "Travel"):
            while not rospy.is_shutdown():
                self.travel()

    def save_map(self):
        command = "rosrun map_server map_saver -f <made_map>"
        os.system(command)

    def home(self):
        return False

    def travel(self):
        pass

if __name__ == '__main__':
    controller = Controller()

    rospy.loginfo("Initializing Controller")
    # rate = rospy.Rate(1000)
    # rate.sleep()
    # while not rospy.is_shutdown() and not controller.explore():
    #     pass

    rospy.spin()