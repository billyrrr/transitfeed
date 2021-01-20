#!/usr/bin/python2.5

# Copyright (C) 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from .gtfsobjectbase import GtfsObjectBase
from . import problems as problems_module
from . import util

class Pathway(GtfsObjectBase):
  """Represents a pathway in a schedule"""
  _REQUIRED_FIELD_NAMES = ['pathway_id', 'from_stop_id', 'to_stop_id', 'pathway_mode', 'is_bidirectional']
  _FIELD_NAMES = _REQUIRED_FIELD_NAMES + ['length', 'traversal_time', 'stair_count', 'max_slope', 'min_width', 'signposted_as', 'reversed_signposted_as']
  _TABLE_NAME = 'pathways'
  _ID_COLUMNS = ['pathway_id']

  def __init__(self, schedule=None,  pathway_id=None, from_stop_id=None, to_stop_id=None, pathway_mode=None,
               is_bidirectional=None, traversal_time=None, field_dict=None):
    self._schedule = None
    if field_dict:
      self.__dict__.update(field_dict)
    else:
      self.pathway_id = pathway_id
      self.from_stop_id = from_stop_id
      self.to_stop_id = to_stop_id
      self.pathway_mode = pathway_mode
      self.traversal_time = traversal_time
      self.is_bidirectional = is_bidirectional

    if getattr(self, 'pathway_mode', None) in ("", None):
      # Use the default, recommended transfer, if attribute is not set or blank
      self.pathway_mode = 2
    else:
      try:
        self.pathway_mode = util.NonNegIntStringToInt(self.pathway_mode)
      except (TypeError, ValueError):
        pass

    if hasattr(self, 'traversal_time'):
      try:
        self.traversal_time = util.NonNegIntStringToInt(self.traversal_time)
      except (TypeError, ValueError):
        pass
    else:
      self.traversal_time = None
    if schedule is not None:
      # Note from Tom, Nov 25, 2009: Maybe calling __init__ with a schedule
      # should output a DeprecationWarning. A schedule factory probably won't
      # use it and other GenericGTFSObject subclasses don't support it.
      schedule.AddPathwayObject(self)

  def ValidateFromStopIdIsPresent(self, problems):
    if util.IsEmpty(self.from_stop_id):
      problems.MissingValue('from_stop_id')
      return False
    return True

  def ValidateToStopIdIsPresent(self, problems):
    if util.IsEmpty(self.to_stop_id):
      problems.MissingValue('to_stop_id')
      return False
    return True

  def ValidatePathwayMode(self, problems):
    if not util.IsEmpty(self.pathway_mode):
      if (not isinstance(self.pathway_mode, int)) or \
          (self.pathway_mode not in range(1, 8)):
        problems.InvalidValue('pathway_mode', self.pathway_mode)
        return False
    return True

  def ValidateMinimumPathwayTime(self, problems):
    if not util.IsEmpty(self.traversal_time):
      if self.pathway_mode != 2:
        problems.MinimumPathwayTimeSetWithInvalidPathwayMode(
            self.pathway_mode)

      # If traversal_time is negative, equal to or bigger than 24h, issue
      # an error. If smaller than 24h but bigger than 3h issue a warning.
      # These errors are not blocking, and should not prevent the transfer
      # from being added to the schedule.
      if (isinstance(self.traversal_time, int)):
        if self.traversal_time < 0:
          problems.InvalidValue('traversal_time', self.traversal_time,
                                reason="This field cannot contain a negative " \
                                       "value.")
        elif self.traversal_time >= 24*3600:
          problems.InvalidValue('traversal_time', self.traversal_time,
                                reason="The value is very large for a " \
                                       "transfer time and most likely " \
                                       "indicates an error.")
        elif self.traversal_time >= 3*3600:
          problems.InvalidValue('traversal_time', self.traversal_time,
                                type=problems_module.TYPE_WARNING,
                                reason="The value is large for a transfer " \
                                       "time and most likely indicates " \
                                       "an error.")
      else:
        # It has a value, but it is not an integer
        problems.InvalidValue('traversal_time', self.traversal_time,
                              reason="If present, this field should contain " \
                                "an integer value.")
        return False
    return True

  def GetPathwayDistance(self):
    from_stop = self._schedule.stops[self.from_stop_id]
    to_stop = self._schedule.stops[self.to_stop_id]
    distance = util.ApproximateDistanceBetweenStops(from_stop, to_stop)
    return distance

  def ValidateFromStopIdIsValid(self, problems):
    if self.from_stop_id not in self._schedule.stops.keys():
      problems.InvalidValue('from_stop_id', self.from_stop_id)
      return False
    return True

  def ValidateToStopIdIsValid(self, problems):
    if self.to_stop_id not in self._schedule.stops.keys():
      problems.InvalidValue('to_stop_id', self.to_stop_id)
      return False
    return True

  def ValidatePathwayDistance(self, problems):
    distance = self.GetPathwayDistance()

    if distance > 10000:
      problems.PathwayDistanceTooBig(self.from_stop_id,
                                      self.to_stop_id,
                                      distance)
    elif distance > 2000:
      problems.PathwayDistanceTooBig(self.from_stop_id,
                                      self.to_stop_id,
                                      distance,
                                      type=problems_module.TYPE_WARNING)

  def ValidatePathwayWalkingTime(self, problems):
    if util.IsEmpty(self.traversal_time):
      return

    if self.traversal_time < 0:
      # Error has already been reported, and it does not make sense
      # to calculate walking speed with negative times.
      return

    distance = self.GetPathwayDistance()
    # If traversal_time + 120s isn't enough for someone walking very fast
    # (2m/s) then issue a warning.
    #
    # Stops that are close together (less than 240m appart) never trigger this
    # warning, regardless of traversal_time.
    FAST_WALKING_SPEED= 2 # 2m/s
    if self.traversal_time + 120 < distance / FAST_WALKING_SPEED:
      problems.PathwayWalkingSpeedTooFast(from_stop_id=self.from_stop_id,
                                           to_stop_id=self.to_stop_id,
                                           transfer_time=self.traversal_time,
                                           distance=distance)

  def ValidateBeforeAdd(self, problems):
    result = True
    result = self.ValidateFromStopIdIsPresent(problems) and result
    result = self.ValidateToStopIdIsPresent(problems) and result
    result = self.ValidatePathwayMode(problems) and result
    result = self.ValidateMinimumPathwayTime(problems) and result
    return result

  def ValidateAfterAdd(self, problems):
    valid_stop_ids = True
    valid_stop_ids = self.ValidateFromStopIdIsValid(problems) and valid_stop_ids
    valid_stop_ids = self.ValidateToStopIdIsValid(problems) and valid_stop_ids
    # We need both stop IDs to be valid to able to validate their distance and
    # the walking time between them
    if valid_stop_ids:
      self.ValidatePathwayDistance(problems)
      self.ValidatePathwayWalkingTime(problems)

  def Validate(self,
               problems=problems_module.default_problem_reporter):
    if self.ValidateBeforeAdd(problems) and self._schedule:
      self.ValidateAfterAdd(problems)

  def _ID(self):
    return tuple(self[i] for i in self._ID_COLUMNS)

  def AddToSchedule(self, schedule, problems):
    schedule.AddPathwayObject(self, problems)
