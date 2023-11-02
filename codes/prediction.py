
class PredictionLogic:
    """
    Author(s): M.Bagga, Shiva

    Description:
    Class for handling Prediction related logics
    (or) in simpler words, create / update Prediction Entries.

    Attributes:

    Methods:
    - updatePrediction --> updates prediction entries
    - startTrip        --> get the prediction status for type 'START_TRIP'
    - midTrip          --> get the prediction status for type 'MID_TRIP'

    """

    # @transaction.atomic
    def updatePrediction(self, predictionType, predictions):
        """
        Author(s): M.Bagga, Shiva

        Description:
        Create or Update predictions

        Parameters:
        - predictionType :
        - predictions    : list of predictions; {
                                             {"tt_id": "", "prediction_data": {"status": } },
                                             {"tt_id": "", "prediction_data": {"status": } },
                                             {"tt_id": "", "prediction_data": {"status": } }
                                             }

        Pseudocode:
        1. Create or Update predictions for the current day and trip combination
        2. returns None (nothing)


        Input:
        Output:
        """
        for trip, prediction in predictions.items():
            print(prediction)
            prediction = Prediction.objects.update_or_create(
                prediction_date=date.today(),
                time_table_id=trip,
                defaults={
                    "prediction_data": prediction,
                    "prediction_action_id": prediction[
                        "status"
                    ],  # --> change to "prediction_action__code" (see model)
                },
            )

    def startTrip(self, trip, past_prediction, position, device):
        """
        Author(s): M.Bagga, Shiva

        Description:
        get the prediction status for the START-TRIP time_table entry based on the current_position and past_prediction of the device/bus

        Parameters:
        - trip             : timetable entry
        - past_prediction  : past Prediction entry (dict)
        - position         : Position object
        - device           : device instance (obj)

        Pseudocode:
        1. if position isn't provided for the device:
            - fetch the latest position obj for that device
        2. get the status for the position<-->past_prediction combination
            - use commonChecks(position, past_prediction)
            - possible values are 'PASS' / 'GPS_OFFLINE' / 'NO_POSITION'
        3. if status='PASS':
              return the status
        4. Get the prediction data (STATUS) by calling checkMovement(current_position, past_prediction, next_adda_arrival_time)
            - Note: for start trip, there's no next_to_next position and from_position
        5. Prediction_data => OFFTRACK_MAX_DIST / OFFTRACK / WRONG_ROUTE / BUS_ADDA_SKIPPED / ON_TRACK
        6. return prediction_data

        """
        if not position and device:
            try:
                position = model_to_dict(
                    Position.objects.filter(device=device).latest("servertime")
                )
            except:
                print(
                    "Error fetching position for device : {d}".format(d=device),
                    sys.exc_info(),
                )
        commonCheck = PredictionUtils().commonChecks(position, past_prediction)
        if commonCheck["status"] != "PASS":
            return commonCheck
        prediction_data = {}
        # Bus didn't travel on this route yesterday
        # if trip['prev_day_arrival_time'] is None:
        #    prediction_data = {'status': "PREV_DAY"}
        prediction_data = PredictionUtils().checkMovement(
            position,
            {"x": trip["stop_point"].x, "y": trip["stop_point"].y},
            None,
            None,
            past_prediction,
            trip["actual_arrival_time"],
        )
        return prediction_data

    def midTrip(
        self,
        position,
        to_timetable,
        from_timetable,
        to_next_timetable,
        past_prediction,
        device,
    ):
        """
        Author(s): M.Bagga, Shiva

        Description:
        get the prediction status for MID-TRIP time_table entry based on the current_position and past_prediction of the device/bus

        Parameters:
        - position          : current position entry
        - to_timetable      : next timetable entry
        - from_timetable    : start timetable entry
        - to_next_timetable : next-to-next timetable entry
        - past_prediction   : past prediction entry (having prediction data and position point)
        - device            : device (obj)

        Pseudocode:
        1. if position isn't provided for the device:
            - fetch the latest position obj for that device
        2. get the status for the position<-->past_prediction combination
            - use commonChecks(position, past_prediction)
            - possible values are 'PASS' / 'GPS_OFFLINE' / 'NO_POSITION'
        3. if status='PASS':
              return the status
        4. if the to_timetable entry has no previous_day_arrival_time, then prediction_data["previous_day_travel"] will be False
        5. else get the prediction data (STATUS) by calling checkMovement:
                - checkMovement(current_position, to_position, to_next_position, from_position, past_prediction, next_adda_arrival_time)
                - Note: for Mid Trip, next_to_next_position and from_position exists (all these can be passed into checkMovement)
        6. Prediction_data => OFFTRACK_MAX_DIST / OFFTRACK / WRONG_ROUTE / BUS_ADDA_SKIPPED / ON_TRACK
        7. return prediction_data

        """
        if not position and device:
            try:
                position = model_to_dict(
                    Position.objects.filter(device=device).latest("servertime")
                )
            except:
                print(
                    "Error fetching position for device : {d}".format(d=device),
                    sys.exc_info(),
                )
        commonCheck = PredictionUtils().commonChecks(position, past_prediction)
        if commonCheck["status"] != "PASS":
            return commonCheck
        prediction_data = {}
        # Bus didn't travel on this route yesterday
        if to_timetable["prev_day_arrival_time"] is None:
            prediction_data = {"prev_day_travel": False}
        prediction_data = PredictionUtils().checkMovement(
            position,
            {"x": to_timetable["stop_point"].x, "y": to_timetable["stop_point"].y},
            {
                "x": to_next_timetable["stop_point"].x,
                "y": to_next_timetable["stop_point"].y,
            }
            if to_next_timetable
            else None,
            {"x": from_timetable["stop_point"].x, "y": from_timetable["stop_point"].y}
            if from_timetable
            else None,
            past_prediction,
            to_timetable["actual_arrival_time"],
        )
        return prediction_data

    def calculateHistoricalETA(self, bus_number, trip_number, position, timetable):
        """
        Author(s): M.Bagga, Shiva

        Description:
        calculates the HistoricalETA for given bus

        Parameters:
        - bus_number        : bus_number (str)
        - trip_number       : timetable id
        - position          : current position obj (containing lat & lon)
        - to_next_timetable : next-to-next timetable entry
        - timetable         : timetable entries as list (orderdby arrival_time)

        Pseudocode:
        1. Calculate the current_point using position.lat & position.lon (use convertToPoint function)
        2. Get the closest historical point to current_point
            - fetch the BusRouteHistory objects for the bus_number and parallely add a distance field (i.e.
                calculated distance between the historical_location & current_location point fields)
            - orderby distance field
            - closest_historical_point_to_curr_pos = filter_result[0]
        3. Get the closest historical point to Next Bus Adda
            - next_bus_adda = timetable[0]
            - calculate the next_bus_adda_point as convertToPoint(next_bus_adda['latitude'], next_bus_adda['longitude'])
            - fetch the BusRouteHistory objects for the bus_number and parallely add a distance field (i.e.
                calculated distance between the historical_location & next_bus_adda_point fields)
            - orderby distance field
            - closest_historical_point_to_next_adda = filter_result[0]

        4. Estimate the ETA to Next Bus Adda
            4.1 Calculate estimated device time (in mins) as:
                est_remaining_time = (closest_historical_point_to_next_adda["devicetime"] - closest_historical_point_to_curr_pos["devicetime"])
            4.2 Calculate remaining time (in mins) to next bus adda:
                remaining_time_mins = (next_bus_adda["actual_arrival_time"] - current_time)
            4.3 Calculate time difference (in mins)
                time_diff_mins = estimated_device_time_mins - remaining_time_mins

            4.4 if time_diff_mins falls within in 30 mins threshold:
                    - return [True, time_diff_mins] --> no ETA / Prediction Action
                else (time_diff_mins crossed threshold):
                    - create / update prediction entry with:
                        - predicted_by status as 'UPDATE_ETA'
                        - prediction_action__code = 'OFFTRACK_MAX_TIME'
                        - prediction_data = {"update_time_mins": time_diff_mins}
                        - return [False, time_diff_mins]
        """
        print("Calculate closest point from Bus History to current position")
        curr_point = CommonUtils().convertToPoint(
            position["latitude"], position["longitude"]
        )
        closest_to_cur_pos = (
            BusRouteHistory.objects.filter(
                bus_number=bus_number,
            )
            .annotate(distance=Distance("location", curr_point))
            .order_by("distance")
            .values()[0]
        )
        # .annotate(closest_point=ClosestPoint("location",
        #            Point(position['latitude'], position['longitude']))).values()
        print("Calculate closest point from Bus History to next bus adda")
        next_bus_adda = timetable[0]
        next_adda_point = CommonUtils().convertToPoint(
            next_bus_adda["latitude"], next_bus_adda["longitude"]
        )
        closest_to_next_adda = (
            BusRouteHistory.objects.filter(
                bus_number=bus_number,
            )
            .annotate(distance=Distance("location", next_adda_point))
            .order_by("distance")
            .values()[0]
        )
        # annotate(closest_point=ClosestPoint("location", next_adda_point)).values()
        print("Estimate eta to next bus adda")
        estimated_device_time_mins = (
            closest_to_next_adda["devicetime"] - closest_to_cur_pos["devicetime"]
        ).total_seconds() / 60
        print("Remaining time in mins")
        remaining_time_mins = (
            datetime.combine(date.today(), next_bus_adda["actual_arrival_time"])
            - datetime.now()
        ).total_seconds() / 60
        # Check if time difference is within acceptable time diff range - 30 mins
        time_diff_mins = (
            estimated_device_time_mins - remaining_time_mins
        ).total_seconds() / 60
        if -30 < time_diff_mins < 30:
            print("Update ETA : {mins} mins".format(mins=time_diff_mins))
            return [True, time_diff_mins]
        else:
            print(
                "Max Threshold crossed (30 mins) for ETA : {mins} mins".format(
                    mins=time_diff_mins
                )
            )
            Prediction.objects.update_or_create(
                timetable_id=timetable["id"],
                prediction_date=date.today(),
                predicted_by=Prediction.UPDATE_ETA,
                prediction_action="OFFTRACK_MAX_TIME",
                prediction_data={"update_time_mins": time_diff_mins},
            )
        return [False, time_diff_mins]
