

class TimeTableAction:
    """
    Author: M.B, Shiva
    Description: Class for handling TimeTable related logics

    Arrtibutes:
    - ROUTE_HISTORY_TIME_BUFFER : time (in minutes) for which the Historical Position points are to be saved
    - TRACCAR_EVENT_TIME_BUFFER : time window (in minutes) within which Traccar Events
                                  can update the timetable if they occur close to the scheduled arrival time of 'adda'.
                                  Events within this time buffer will be considered for timetable updates.

    Methods:
    - generateHistoryRoute --> generate 5 mins position route history for a device / bus
    - generateHistoryRoute --> generate 5 mins position route history for all devices / buses
    - updateETA            --> update the ETA for timetables
    - enterExitEvent       --> fetch the active TT entries to update the ETA based on ENTER/EXIT events
    """

    # Historical Positions Points to be saved with gap of 5 minutes
    ROUTE_HISTORY_TIME_BUFFER = 5  # minutes

    # Traccar Events can update Timetable if within 2 hours of actual_arrival_time of adda
    TRACCAR_EVENT_TIME_BUFFER = 60 * 2  # minutes

    def generateHistoryRouteAll(self, from_date, to_date):
        """
        Author: M.Bagga, Shiva

        Description:
        Creates BusHistoricalRoute instances for all the devices in the given date range.

        Parameters:
        - from_date : datetime obj
        - to_date   : datetime obj

        Pseudocode:
        1. fetch all the Devices
        2. for device in Devices:
            - call the generateHistoryRoute function that will create the BusRouteHistory instances
              for each device considering the ROUTE_HISTORY_TIME_BUFFER
            - iterate with a sleep of 5 secs
        3. returns None (nothing)

        Input:
        Output:
        """

        print("Fetching All Active Devices")
        devices = list(Device.objects.all().values())
        """Position.objects.filter(
                servertime__gte = from_date,
                servertime__lte = to_date).distinct('device_id').values('device_id')"""
        for device in devices:
            print("Bus : %s" % device["name"])
            self.generateHistoryRoute(device["name"], from_date, to_date, device["id"])
            time.sleep(5)


    def generateHistoryRoute(self, bus_number, from_date, to_date, deviceId):
        """
        Author: M.Bagga, Shiva

        Description:
        creates BusRouteHistory instances for all the positions that are recorded in the
        given (from_date, to_date) range

        Parameters:
        - bus_number (str)      : Bus Number (same as Device Name)
        - from_date (datetime)  : from date
        - to_date (datetime)    : to date
        - deviceId (int)        : Device ID

        Pseudocode:
        1. Delete the existing BusRouteHistory (if any) in the given date range
        2. Fetch the Position objects in the given datetime range (ordered by server_time) --> first entry as START position
        3. if no Position Objects in datetime range, returns "No Positions"
            else:
                - initialize start_time = pos[0]['device_time']
                - for all the positions other than positions[0], create corresponding BusRouteHistory instances if the position['device_time'] > start_time
                    - increase the start_time by ROUTE_HISTORY_TIME_BUFFER (to account for gap before saving the next historical record)
                    - this filters out the positions that are prior to start_time
        4. returns None (nothing)

        Input:
        Output:

        """
        print("Deleting Bus Route History")

        BusRouteHistory.objects.filter(
            bus_number=bus_number, servertime__range=(from_date, to_date)
        ).delete()

        print("Fetching Positions")

        positions = list(
            Position.objects.filter(
                device_id=deviceId, servertime__range=(from_date, to_date)
            )
            .order_by("servertime")
            .values()
        )
        if len(positions) < 1:
            print("No Positions")
            return
        start_time = positions[0]["devicetime"]
        print("Creating Bus Route History")
        with transaction.atomic():
            for pos in positions:
                if pos["devicetime"] >= start_time:
                    BusRouteHistory.objects.create(
                        bus_number=bus_number,
                        servertime=pos["servertime"],
                        fixtime=pos["fixtime"],
                        devicetime=pos["devicetime"],
                        location=Point(pos["latitude"], pos["longitude"]),
                    )
                start_time += timedelta(minutes=self.ROUTE_HISTORY_TIME_BUFFER)
        return

    # @transaction.atomic
    def updateETA(self, timetable, time_diff_mins, event_type="arrival"):
        """
        Author: M.Bagga, Shiva

        Description:
        Updates the arrival/departure time of the timetable instance by the given time_difference
        (or) in simpler words, updates the ETA.

        Parameters:
        - timetable      (list): timetable dictionaries (for a single trip)
        - time_diff_mins : int (time in minutes by which the arrival time must be updated in the timetable)
        - event_type     : "arrival" or "departure"

        Pseudocode:
        1. fetch all TimeTable instances based on the IDs in the timetable list
        2. update the arrival/departure time by the time_diff_mins value
            - the update can happen for both arrival & departure time
        3. returns None (nothing)

        """
        # update the arrival / departure time based on the EVENT triggered
        TimeTable.objects.filter(id__in=list(map(lambda x: x["id"], timetable))).update(
            **{
                "actual_{tfield}_time".format(tfield=event_type): (
                    datetime.combine(
                        date.today(),
                        F("actual_{tfield}_time".format(tfield=event_type)),
                    )
                    + timedelta(minutes=time_diff_mins)
                ).time()
            }
        )

        return

    def enterExitEvent(self, bus_number, bus_adda, event_type, event_time):
        """
        Author: M.Bagga, Shiva

        Description:
        Updates the TimeTable entries for all trips based on ENTER/EXIT trigger event

        Parameters:
        - bus_number (str): Bus Number
        - bus_adda   (str <uuid>): Bus Adda/Stop id
        - event_type : "ENTER" or "EXIT"
        - event_time : Event trigger time

        Pseudocode:
        1. fetch the timetable instances for given <bus_number -- bus_adda> combination
            --> orderby increasing arrival time (indirectly ordering by stops sequence)
        2. return if no timetable exists
        3. if multiple timetable_objs exists:
                - fetch all the active (is_active=True) timetable_objs with distinct bus_number<->trip_number combination
                  the trip_number should be
                - if active_timetable_objs exist:
                    - filter the timetable_objs with 1st active trip
                - else (no active time_table objs):
                    - get the previous_day time_table entries by prev_day_arrival_time

                    - if previous_day schedule exists:
                        - get the starting stop timetable_obj
                    - else (no previous day schedule):
                        - get the timetable_objs with stop_type as 'S' (start addas)
                        - if all objs have stop_type=='S':
                            (return) --> let ETA handle
                        - elif (no active trip with start adda):
                            - possible that the route changed.
                            - create a prediction event with prediction_action_code='ROUTE_CHAGE'
                        - else (stop_type='M'ID):
                            - prediction_action_code='MID_TRIP_START'

            else (single timetable exists):
                - get the first tt_obj

        4. Make the tt_obj with (actual_arrival_time < tt_obj.actual_arrival_time) as INACTIVE (is_active=False)
            - ensuring not to update the arrival time of passed bus addas (i.e. previous bus_addas)
        5. Calculate the time_diff_mins
        6. Fetch the list of IDs of active (is_active=True) timetable entries for the current trip
        7. Update the ETA for those entries
            - time_field = "arrival" if event_type='ENTER' else 'departure'
            - updateETA(timetable_list_to_update, time_diff_mins, time_field=time_field)

        8. returns None (nothing)
        """

        print(
            "Event : {event} for Bus {bus} on Bus Adda : {adda}".format(
                event_type, bus_number, bus_adda
            )
        )

        timetable_objs = (
            TimeTable.objects.filter(bus_number=bus_number, stop_id=bus_adda)
            .order_by("actual_arrival_time")
            .values()
        )
        if not timetable_objs:
            print("No TimeTable")
            return
        if len(timetable_objs) > 1:
            # Multiple Timetable with same bus adda
            # Check if any active trip
            active_timetable = list(
                TimeTable.objects.filter(
                    bus_number=bus_number,
                    trip_number__in=list(
                        map(lambda x: x["trip_number"], timetable_objs)
                    ),
                    is_active=True,
                )
                .distinct("bus_number", "trip_number")
                .values("bus_number", "trip_number")
            )
            if active_timetable:
                # Active TimeTable to update
                timetable_objs = list(
                    filter(
                        lambda x: x["trip_number"]
                        == active_timetable[0]["trip_number"],
                        timetable_objs,
                    )
                )
            else:
                # Check if bus was on any of the timetable prev day (Prefering that route)
                prev_day_timetable = list(
                    filter(lambda y: y["prev_day_arrival_time"], timetable_objs)
                )
                if prev_day_timetable:
                    # Prev Day Schedule Exist
                    timetable_obj = prev_day_timetable[0]
                else:
                    # Check inactive trips (multiple route mapped)
                    # Check if bus adda is starting adda
                    start_addas = list(
                        filter(
                            lambda x: x["stop_type"] == "S", timetable_objs
                        )  # ------> this line only returns single obj (changed to timetable_objs)
                    )
                    if start_addas:
                        # Check if all trips have same start addas
                        if len(start_addas) > 1:
                            # Start Adda for all TimeTables > Wait for POS or handle in ETA
                            return
                        elif len(start_addas) == 1:
                            # No Active Trip with start adda Event > Possible Route Changed
                            Prediction.objects.create(
                                predicted_by=Prediction.TRACCAR_EVENT,
                                time_table_id=start_addas[0]["id"],
                                prediction_action_id="ROUTE_CHANGE",
                                prediction_date=date.today(),
                            )
                            return
                        else:
                            # No Active Trips and Bus Adda is in mid > Activate Timetable
                            Prediction.objects.create(
                                predicted_by=Prediction.TRACCAR_EVENT,
                                time_table_id=start_addas[0]["id"],
                                prediction_action_id="MID_TRIP_START",
                                prediction_date=date.today(),
                            )
                            return
        else:
            # Single TImetable
            timetable_obj = timetable_obj[0]

        # Check timetable entries before adda > Not updating arriv time of prev addas
        TimeTable.objects.filter(
            bus_number=bus_number,
            trip_number=timetable_obj["trip_number"],
            actual_arrival_time__lte=timetable_obj["actual_arrival_time"],
            is_active=True,
        ).update(is_active=False)

        # calculate time difference in minutes
        time_diff_mins = (
            datetime.combine(date.today(), event_time)  # ----> ask whats event time?
            - datetime.combine(date.today(), timetable_obj["actual_arrival_time"])
        ).total_seconds() / 60

        # timetable entries to be updated
        timetable_to_update = list(
            TimeTable.objects.filter(
                bus_number=bus_number,
                trip_number=timetable_obj["trip_number"],
                is_active=True,
            ).values("id")
        )
        self.updateETA(
            timetable_to_update,
            time_diff_mins,
            "departure" if event_type == "EXIT" else "arrival",
        )
        return
