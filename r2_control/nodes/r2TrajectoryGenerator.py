#! /usr/bin/env python

import roslib; roslib.load_manifest('r2_control')
import rospy
import actionlib
import math
import random

from control_msgs.msg import *
from trajectory_msgs.msg import *
from industrial_msgs.srv import *
from sensor_msgs.msg import JointState
from copy import copy, deepcopy

TORAD = math.pi/180.0
TODEG = 1.0/TORAD

class R2TrajectoryGenerator :

    def __init__(self, N, wp, arm):

        self.arm = arm
        self.currentData = None
        self.desiredData = None
        self.deadlineData = None

        self.currentState = JointState()
        self.currentState.position = [0]*N
        self.currentState.velocity = [0]*N
        self.currentState.effort = [0]*N
        self.numJoints = N
        self.waypoints = wp

        self.fingers = [("index",4),("middle",4),("ring",3),("little",3),("thumb",4)]

        rospy.Subscriber("/r2/joint_states", JointState, self.jointStateCallback)



        if self.arm=="left" :
            self.trajPublisher = rospy.Publisher('/r2/l_arm_controller/command', JointTrajectory)
            self.trajClient = actionlib.SimpleActionClient('r2/l_arm_controller/follow_joint_trajectory', FollowJointTrajectoryAction)
        elif self.arm=="right" :
            self.trajPublisher = rospy.Publisher('/r2/r_arm_controller/command', JointTrajectory)
            self.trajClient = actionlib.SimpleActionClient('r2/r_arm_controller/follow_joint_trajectory', FollowJointTrajectoryAction)
        elif self.arm=="left_hand" :
            self.trajPublisher = rospy.Publisher('/r2/l_hand_controller/command', JointTrajectory)
            self.trajClient = actionlib.SimpleActionClient('r2/l_hand_controller/follow_joint_trajectory', FollowJointTrajectoryAction)
        elif self.arm=="right_hand" :
            self.trajPublisher = rospy.Publisher('/r2/r_hand_controller/command', JointTrajectory)
            self.trajClient = actionlib.SimpleActionClient('r2/r_hand_controller/follow_joint_trajectory', FollowJointTrajectoryAction)
        elif self.arm=="neck" :
            self.trajPublisher = rospy.Publisher('/r2/neck_controller/command', JointTrajectory)
            self.trajClient = actionlib.SimpleActionClient('r2/neck_controller/follow_joint_trajectory', FollowJointTrajectoryAction)
        else :
            rospy.logerr("R2TrajectoryGenerator::R2TrajectoryGenerator() -- unknown arm")

        self.trajClient.wait_for_server()

        self.actionGoal = FollowJointTrajectoryGoal()


    def getNumJoints(self) :
        return self.numJoints

    def jointStateCallback(self, data):
        # if self.numJoints != len(data.position) or self.numJoints != len(data.name) :
        #     rospy.logerr("R2TrajectoryGenerator::jointStateCallback() -- /joint_states has different number of joints!")
        # else :
        #     print "asfasfds", data
        self.currentState = data

    def computeTrajectory(self, desiredData, deadline):

        jointTraj = JointTrajectory()
        currentState = copy(self.currentState)
        desiredState = copy(desiredData)

        # create simple lists of both current and desired positions, based on provided desired names
        rospy.loginfo("R2TrajectoryGenerator::computeTrajectory() -- finding necessary joints")
        desiredPositions = []
        currentPositions = []
        # print desiredData
        for desIndex in range(len(desiredState.name)) :
            for curIndex in range(len(currentState.name)) :
                if ( desiredState.name[desIndex] == currentState.name[curIndex] ) :
                    desiredPositions.append(desiredState.position[desIndex])
                    currentPositions.append(currentState.position[curIndex])

        rospy.loginfo("R2TrajectoryGenerator::computeTrajectory() -- creating trajectory")
        jointTraj.joint_names = desiredState.name
        jointTraj.points = list()

        for j in range(self.waypoints) :
            trajPoint = JointTrajectoryPoint()

            t = (deadline / self.waypoints) * (j + 1)
            trajPoint.time_from_start = rospy.Duration(t)

            trajPoint.positions = list()
            for i in range(len(desiredPositions)) :
                # simple linear progression, needs to be replaced with something better
                #trajPoint.positions.append( currentPositions[i] + ( (desiredPositions[i] - currentPositions[i]) * ((j+1) / self.waypoints) ) )
                trajPoint.positions.append( self.minJerk(currentPositions[i], desiredPositions[i], deadline, t) )

            jointTraj.points.append(trajPoint)

        rospy.loginfo("R2TrajectoryGenerator::moveToGoal() -- using tolerances")
        # print jointTraj

        return jointTraj


    def minJerk(self, start, end, duration, t):
        tOverD = float(t) / float(duration)
        return start + (end - start)*( 10*math.pow(tOverD,3) - 15*math.pow(tOverD,4) + 6*math.pow(tOverD,5) )

    def moveToGoal(self, jointGoal, deadline, useTolerances) :

        #self.trajPublisher.publish(self.computeTrajectory(jointGoal, deadline))
        self.actionGoal.trajectory = self.computeTrajectory(jointGoal, deadline)

        # print "srv:", self.cmdTrajectory(self.actionGoal.trajectory)
        offset = 0

        if useTolerances :
            rospy.loginfo("R2TrajectoryGenerator::moveToGoal() -- using tolerances")
            self.actionGoal.path_tolerance = []
            self.actionGoal.goal_tolerance = []

            if self.arm == "left_hand" :
                for k in range(len(self.fingers)):
                    for j in range(self.fingers[k][1]):
                        tol.name = "/r2/left_arm/hand/" + self.fingers[k][0] + "/joint" + str(j+offset)
                        tol.position = 0.2
                        tol.velocity = 1
                        tol.acceleration = 10
                        self.actionGoal.path_tolerance.append(tol)
                        self.actionGoal.goal_tolerance.append(tol)
            elif self.arm == "right_hand" :
                for k in range(len(self.fingers)):
                    for i in range(self.fingers[k][1]):
                        tol.name = "/r2/right_arm/hand/" + self.fingers[k][0] + "/joint" + str(j+offset)
                        print tol.name
                        tol.position = 0.2
                        tol.velocity = 1
                        tol.acceleration = 10
                        self.actionGoal.path_tolerance.append(tol)
                        self.actionGoal.goal_tolerance.append(tol)
            else :
                for i in range(self.numJoints):
                    tol = JointTolerance()
                    if self.arm == "left" or self.arm == "right" :
                        tol.name = "/r2/" + self.arm + "_arm/joint" + str(i+offset)
                    elif self.arm == "neck" :
                        tol.name = "/r2/" + self.arm + "/joint" + str(i+offset)
                    tol.position = 0.2
                    tol.velocity = 1
                    tol.acceleration = 10

                    self.actionGoal.path_tolerance.append(tol)
                    self.actionGoal.goal_tolerance.append(tol)

        else :
            rospy.loginfo("R2TrajectoryGenerator::moveToGoal() -- not using tolerances")

        self.actionGoal.goal_time_tolerance = rospy.Duration(10.0)

        # send goal nad monitor response
        self.trajClient.send_goal(self.actionGoal)
        # self.trajClient.wait_for_result(rospy.Duration.from_sec(4.0))

        rospy.loginfo("R2TrajectoryGenerator::moveToGoal() -- returned state: %s", str(self.trajClient.get_state()))
        rospy.loginfo("R2TrajectoryGenerator::moveToGoal() -- returned result: %s", str(self.trajClient.get_result()))

        return

    def formatJointStateMsg(self, j, offset) :

        if not (len(j) == self.numJoints) :
            rospy.logerr("R2TrajectoryGenerator::formatJointStateMsg() -- incorrectly sized joint message")
            return None

        js = JointState()
        js.header.seq = 0
        js.header.stamp = rospy.Time.now()
        js.header.frame_id = ""
        js.name = []
        js.position = []


        if self.arm == "left" or self.arm == "right" :
            for i in range(self.numJoints):
                js.name.append("/r2/" + self.arm + "_arm/joint" + str(i+offset))
                js.position.append(j[i])
        if self.arm == "left_hand" :
            for k in range(len(self.fingers)):
                for i in range(self.fingers[k][1]):
                    js.name.append("/r2/left_arm/hand/" + self.fingers[k][0] + "/joint" + str(i+offset))
                    js.position.append(j[i])
        if self.arm == "right_hand" :
            for k in range(len(self.fingers)):
                for i in range(self.fingers[k][1]):
                    js.name.append("/r2/right_arm/hand/" + self.fingers[k][0] + "/joint" + str(i+offset))
                    js.position.append(j[i])
        elif self.arm == "neck" :
            for i in range(self.numJoints):
                js.name.append("/r2/" + self.arm + "/joint" + str(i+offset))
                js.position.append(j[i])

        return js


if __name__ == '__main__':
    rospy.init_node('r2TrajectoryGenerator')
    try:
        r2TrajectoryGeneratorLeft = R2TrajectoryGenerator(7, 500, "left")
        r2TrajectoryGeneratorRight = R2TrajectoryGenerator(7, 500, "right")
        r2TrajectoryGeneratorNeck = R2TrajectoryGenerator(3, 500, "neck")
        r2TrajectoryGeneratorLeftHand = R2TrajectoryGenerator(15, 10, "left_hand")
        r2TrajectoryGeneratorRightHand = R2TrajectoryGenerator(15, 10, "right_hand")
        rospy.sleep(2)


        lhrp = [0]*15
        rhrp = [0]*15

        for i in range(3) :

            lrp = [50.0*TORAD, -80.0*TORAD, -105.0*TORAD, -140.0*TORAD, 80.0*TORAD, 0.0*TORAD, 0.0*TORAD]
            rrp = [-50.0*TORAD, -80.0*TORAD, 105.0*TORAD, -140.0*TORAD, -80.0*TORAD, 0.0*TORAD, 0.0*TORAD]
            nrp = [-20.0*TORAD, 0.0*TORAD, -15.0*TORAD]
            print "ready pose"


            jointGoalLeft = r2TrajectoryGeneratorLeft.formatJointStateMsg(lrp, 0)
            jointGoalRight = r2TrajectoryGeneratorRight.formatJointStateMsg(rrp, 0)
            jointGoalNeck = r2TrajectoryGeneratorNeck.formatJointStateMsg(nrp, 0)
            jointGoalLeftHand = r2TrajectoryGeneratorLeftHand.formatJointStateMsg(lhrp, 0)
            jointGoalRightHand = r2TrajectoryGeneratorRightHand.formatJointStateMsg(rhrp, 0)
            r2TrajectoryGeneratorLeft.moveToGoal(jointGoalLeft, 0.5, False)
            r2TrajectoryGeneratorRight.moveToGoal(jointGoalRight, 0.5, False)
            r2TrajectoryGeneratorLeftHand.moveToGoal(jointGoalLeftHand, 0.1, False)
            r2TrajectoryGeneratorRightHand.moveToGoal(jointGoalRightHand, 0.1, False)
            r2TrajectoryGeneratorNeck.moveToGoal(jointGoalNeck, 0.5, False)

            rospy.sleep(4)

            lrp = [0.0, 0.0, 0.0, -0.0, 0.0, 0.0, 0.0]
            rrp = [0.0, 0.0, 0.0, -0.0, 0.0, 0.0, 0.0]
            nrp = [-5.0*TORAD, 0.0*TORAD, -5.0*TORAD]
            print "zero pose"


            jointGoalLeft = r2TrajectoryGeneratorLeft.formatJointStateMsg(lrp, 0)
            jointGoalRight = r2TrajectoryGeneratorRight.formatJointStateMsg(rrp, 0)
            jointGoalNeck = r2TrajectoryGeneratorNeck.formatJointStateMsg(nrp, 0)
            jointGoalLeftHand = r2TrajectoryGeneratorLeftHand.formatJointStateMsg(lhrp, 0)
            jointGoalRightHand = r2TrajectoryGeneratorRightHand.formatJointStateMsg(rhrp, 0)
            r2TrajectoryGeneratorLeft.moveToGoal(jointGoalLeft, 0.1, False)
            r2TrajectoryGeneratorRight.moveToGoal(jointGoalRight, 0.1, False)
            r2TrajectoryGeneratorLeftHand.moveToGoal(jointGoalLeftHand, 0.1, False)
            r2TrajectoryGeneratorRightHand.moveToGoal(jointGoalRightHand, 0.1, False)
            r2TrajectoryGeneratorNeck.moveToGoal(jointGoalNeck, 0.1, False)

            rospy.sleep(4)

    except rospy.ROSInterruptException:
        pass



