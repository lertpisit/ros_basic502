#! /usr/bin/env python

# original src : https://github.com/ros-teleop/teleop_twist_keyboard
# modified by Lertpisit T.
# 28/05/2021
from __future__ import print_function

import threading
import rospy
from geometry_msgs.msg import Twist

import sys, select, termios, tty

msg = """
using teleoperation keyboard mode
-----------------------------------
move robot by using num pad
    7   8   9
    4   5   6
    1   2   3
-----------------------------------
CTRL-C to quit
"""


class RobotTeleop(threading.Thread):
    def __init__(self, rate):
        super(RobotTeleop, self).__init__()
        self.publisher = rospy.Publisher('cmd_vel', Twist, queue_size = 1)
        
        self.condition = threading.Condition()
        self.done = False

        # Set timeout to None if rate is 0 (causes new_message to wait forever
        # for new data to publish)
        if rate != 0.0:
            self.timeout = 1.0 / rate
        else:
            self.timeout = None
        self.start()

    def update(self, speed, turn):
        self.condition.acquire()
        self.speed = speed
        self.turn = turn
        # Notify publish thread that we have a new message.
        self.condition.notify()
        self.condition.release()

    def stop(self):
        self.done = True
        self.update(0, 0)
        self.join()

    def run(self):
        twist = Twist()
        while not self.done:
            self.condition.acquire()
            # Wait for a new message or timeout.
            self.condition.wait(self.timeout)
            twist.linear.y = 0
            twist.linear.z = 0
            twist.angular.x = 0
            twist.angular.y = 0
            # Copy state into twist message.
            twist.linear.x = self.speed

            twist.angular.z = self.turn

            self.condition.release()

            # Publish.
            self.publisher.publish(twist)

        # Publish stop message when thread exits.
        twist.linear.x = 0
        twist.linear.y = 0
        twist.linear.z = 0
        twist.angular.x = 0
        twist.angular.y = 0
        twist.angular.z = 0
        self.publisher.publish(twist)


def getKey(key_timeout):
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], key_timeout)
    if rlist:
        key = sys.stdin.read(1)
    else:
        key = ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


if __name__=="__main__":
    settings = termios.tcgetattr(sys.stdin)

    rospy.init_node('teleop_twist_keyboard')

    speed = rospy.get_param("~speed", 0)
    turn = rospy.get_param("~turn", 0)
    repeat = rospy.get_param("~repeat_rate", 0.0)
    key_timeout = rospy.get_param("~key_timeout", 0.0)
    if key_timeout == 0.0:
        key_timeout = None

    pub_thread = RobotTeleop(repeat)


    try:
        pub_thread.update(speed, turn)

        print(msg)
        
        while(1):
            key = getKey(key_timeout)
            if key == '8' :
                speed = 0.5
                turn = 0
            elif key == '6':
                speed = 0
                turn = -1
            elif key == '4':
                speed = 0
                turn = 1
            elif key == '2':
                speed = -0.5
                turn = 0

            elif key == '7':
                speed = 0.5
                turn = 0.5
            elif key == '9':
                speed = 0.5
                turn = -0.5
            elif key == '1':
                speed = -0.5
                turn = -0.5
            elif key =='3':
                speed = -0.5
                turn = 0.5
            else:
                speed = 0
                turn = 0
                # Skip updating cmd_vel if key timeout and robot already
                # stopped.
                if (key == '\x03'):
                    break
 
            pub_thread.update(speed, turn)

    except Exception as e:
        print(e)

    finally:
        pub_thread.stop()

        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
