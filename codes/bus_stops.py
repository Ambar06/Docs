class BusStopsUtils:
    """
    Author: Ambar
    This class handles bus stop data and operations.
    PSEUDOCODE:
    CLASS BusStopsUtils
    Author: Ambar
    Initialize BusStopsUtils instance with bus_number, from_date, to_date and config_data

    FUNCTION haversine(lat1, lon1, lat2, lon2)
        R = 6371000
        Convert latitudes and longitudes to radians
        Calculate dlat and dlon
        Calculate a, c, and distance
        RETURN distance
    END FUNCTION

    FUNCTION is_in_range(p1, p2, range)
        Calculate the distance using haversine function
        IF distance <= range
            PRINT "True is_in_range"
            RETURN True
        ELSE
            PRINT "False is_in_range"
            RETURN False
        END IF
    END FUNCTION

    FUNCTION load_stop(data, api_type)
        Set result and status attributes
        Try to get StopStatus and Config objects
        IF result is not None
            IF api_type is "mp_predicted"
                Create a list of PredictedStop objects with data
            ELSE
                Create a list of PredictedStop objects with different data
            END IF
            Bulk create PredictedStop objects
            Get created entries' IDs
            PRINT created entry IDs
            Write created entry IDs to a log file
            RETURN created entry IDs
        END IF
        RETURN None
    END FUNCTION

    FUNCTION compare_mp_stop()
        Create AnalysisData object
        Get new_mp_stops and config_Data
        IF new_mp_stops is not None
            Set api_type to "mp_predicted"
            Get old_mp_stops
            Initialize new_records list
            Iterate through new_mp_stops
                Initialize check_range list
                IF new_stop is in new_records
                    Continue
                IF new_stop is not None
                    Convert new_stop to a point
                    Iterate through old_mp_stops
                        IF new_stop is in new_records
                            Continue
                        Convert old_stop to a point
                        Calculate the result of is_in_range
                        IF result is True
                            PRINT "It's in the range"
                            Append True to check_range
                        ELSE
                            PRINT "It's not in the range...adding stop to the list."
                            Append False to check_range
                        END IF
                    IF any(check_range) is True
                        PRINT "bus_number : {new_stop['bus_number']} has no new stop that is not in the range of {config_Data['geofence_radius']} meters from the previous stops."
                        Continue
                    ELSE
                        Append new_stop to new_records
                    END IF
                ELSE
                    PRINT "new_stop was None"
                END IF
            IF new_records length is greater than 0
                Call load_stop with new_records and api_type
                PRINT "CREATED STOP ID'S:", predicted_stops
            ELSE
                PRINT "NO NEW STOPS CREATED"
            END IF
        ELSE
            PRINT "new_mp_stops were None"
        END IF
    END FUNCTION

    FUNCTION compare_ab_stop()
        Create AnalysisData object
        Get new_ab_stops
        IF new_ab_stops is not None
            Set api_type to "ab_predicted"
            Get old_ab_stops
            Initialize new_records list
            Iterate through new_ab_stops
                Initialize check_range list
                IF new_stop is in new_records
                    Continue
                IF new_stop is not None
                    Convert new_stop to a point
                    Iterate through old_ab_stops
                        IF new_stop is in new_records
                            Continue
                        Convert old_stop to a point
                        Calculate the result of is_in_range
                        IF result is True
                            PRINT "It's in the range"
                            Append True to check_range
                        ELSE
                            PRINT "It's not in the range...adding stop to the list."
                            Append False to check_range
                        END IF
                    IF any(check_range) is True
                        PRINT "bus_number : {new_stop['bus_number']} has no new stop that is not in the range of {config_Data['geofence_radius']} meters from the previous stops."
                        Continue
                    ELSE
                        Append new_stop to new_records
                    END IF
                ELSE
                    PRINT "new_stop was None"
                END IF
            IF new_records length is greater than 0
                PRINT check_range
                Call load_stop with new_records and api_type
                PRINT "CREATED STOP ID'S:", predicted_stops
                PRINT "Created"
            ELSE
                PRINT "NO NEW STOPS CREATED."
            END IF
        ELSE
            PRINT "new_ab_stops were None"
        END IF
        END FUNCTION
    END CLASS
    """

    def __init__(self, bus_number, from_date, to_date):
        """
        Author: Ambar
        Initialize a BusStopsUtils instance.

        Args:
            bus_number (str): The bus number for which you want to create new stops.
            from_date (str): Start date to fetch existing records from the table.
            to_date (str): End date to fetch existing records from the table.
        """
        self.config_Data = Config.objects.order_by("-created_at").values().first()
        self.bus_number = bus_number
        self.from_date = from_date
        self.to_date = to_date

    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        return distance

    @classmethod
    def is_in_range(cls, p1, p2, range):
        """
        Author: Ambar
        Check if two points are within a specified range.

        Args:
            p1 (Point: tuple): The first point to check.
            p2 (Point: tuple): The second point to check.
            range (int): The maximum distance range.

        Returns:
            bool: True if the points are within the range, False otherwise.
        """
        lat1, lon1 = p1
        lat2, lon2 = p2
        distance = cls.haversine(lat1, lon1, lat2, lon2)
        print("distance:", distance)

        if distance <= range:
            print("True is_in_range")
            return True
        else:
            print("False is_in_range")
            return False

    @staticmethod
    def distance_to_decimal_degrees(distance, latitude):
        """
        Source of formulae information:
            1. https://en.wikipedia.org/wiki/Decimal_degrees
            2. http://www.movable-type.co.uk/scripts/latlong.html
        :param distance: an instance of `from django.contrib.gis.measure.Distance`
        :param latitude: y - coordinate of a point/location
        """
        lat_radians = latitude * (math.pi / 180)
        # 1 longitudinal degree at the equator equal 111,319.5m equiv to 111.32km
        return distance.m / (111_319.5 * math.cos(lat_radians))

    def load_stop(self, data, api_type):
        """
        Author: Ambar
        Load new bus stops into the database.

        Args:
            data (DataFrame): The data to load into the database.
            api_type (str): The type of API data.

        Returns:
            created_entry_ids (list) or None: The result of the operation.
        """
        self.result = data
        self.status = "created"

        try:
            self.status = StopStatus.objects.get(status_name=self.status)
            self.config = Config.objects.order_by("-created_at").first()
        except StopStatus.DoesNotExist:
            self.status = None
            self.config = None

        if self.result:
            if api_type == "mp_predicted":
                predicted_stops_objects = [
                    PredictedStop(
                        config=self.config,
                        status=self.status,
                        bus_number=item.get("bus_number"),
                        boarding_point=convertToPoint(
                            item.get("latitude"), item.get("longitude")
                        ),
                        latitude=item.get("latitude"),
                        longitude=item.get("longitude"),
                        duration=item.get("stop_duration"),
                        prediction_type=api_type,
                    )
                    for item in self.result
                ]
            else:
                predicted_stops_objects = [
                    PredictedStop(
                        config=self.config,
                        status=self.status,
                        bus_number=item.get("bus_number"),
                        boarding_point=convertToPoint(
                            item.get("latitude"), item.get("longitude")
                        ),
                        latitude=item.get("latitude"),
                        longitude=item.get("longitude"),
                        stop_name=item.get("name"),
                        prediction_type=api_type,
                    )
                    for item in self.result
                ]

            created_objects = PredictedStop.objects.bulk_create(predicted_stops_objects)
            created_entries = PredictedStop.objects.filter(
                id__in=[obj.id for obj in created_objects]
            )
            created_entry_ids = created_entries.values_list("id", flat=True)
            print(created_entry_ids.values())
            with open(
                "/home/ubuntu/prediction_dashboard_ambar/bus_stop/log_text.txt", "a"
            ) as file:
                file.write(str(created_entry_ids.values()))
            return created_entry_ids
        return None

    def compare_mp_stop(self):
        """
        Author: Ambar
        Compare and update bus stops using MP (MovingPandas) data and call load_stop method to load the data.
        """
        analysis = AnalysisData(self.bus_number, self.from_date, self.to_date)
        self.new_mp_stops = analysis.predicted_data_stops()
        try:
            if self.new_mp_stops is not None:
                api_type = "mp_predicted"
                old_mp_stops = PredictedStop.objects.filter(
                    bus_number=self.bus_number
                ).values()
                new_records = []
                for new_stop in self.new_mp_stops:
                    check_range = []
                    if new_stop in new_records:
                        continue
                    if new_stop is not None:
                        print(new_stop)
                        p1 = convertToPoint(
                            new_stop.get("latitude", None),
                            new_stop.get("longitude", None),
                        )
                        for old_stop in old_mp_stops:
                            if new_stop in new_records:
                                continue
                            p2 = convertToPoint(
                                old_stop.get("latitude", None),
                                old_stop.get("longitude", None),
                            )
                            result = self.is_in_range(
                                p1, p2, self.config_Data["geofence_radius"]
                            )
                            if result == True:
                                print("It's in the range")
                                check_range.append(True)
                                pass
                            else:
                                check_range.append(False)
                        if any(check_range):
                            print(
                                f"bus_number : {new_stop.get('bus_number')} has no new stop that is not in the range of{self.config_Data['geofence_radius']} meters from the previous stops."
                            )
                            pass
                        else:
                            new_records.append(new_stop)
                    else:
                        print("new_stop was None")
                if len(new_records) > 0:
                    predicted_stops = self.load_stop(new_records, api_type)
                    print("CREATED STOP ID'S:", predicted_stops)
                    self.auto_attach_stop(predicted_stops)
                else:
                    print("NO NEW STOPS CREATED")
            else:
                print("new_mp_stops were None")
        except Exception as e:
            print(e)

    def compare_ab_stop(self):
        """
        Author: Ambar
        Compare and update bus stops using AB (ApniBus) data."""
        analysis = AnalysisData(self.bus_number, self.from_date, self.to_date)
        self.new_ab_stops = analysis.intersect_positions_cordinates()
        try:
            if self.new_ab_stops is not None:
                api_type = "ab_predicted"
                old_ab_stops = PredictedStop.objects.filter(
                    bus_number=self.bus_number
                ).values()
                new_records = []
                for new_stop in self.new_ab_stops:
                    check_range = []
                    if new_stop in new_records:
                        continue
                    if new_stop is not None:
                        print(new_stop)
                        p1_ab = convertToPoint(
                            new_stop.get("latitude", None),
                            new_stop.get("longitude", None),
                        )
                        for old_stop in old_ab_stops:
                            if new_stop in new_records:
                                continue
                            p2_ab = convertToPoint(
                                old_stop.get("latitude", None),
                                old_stop.get("longitude", None),
                            )
                            result = self.is_in_range(
                                p1_ab, p2_ab, self.config_Data["geofence_radius"]
                            )
                            if result == True:
                                print("It's in the range")
                                check_range.append(True)
                                pass
                            else:
                                print(
                                    "It's not in the range...adding stop to the list."
                                )
                                check_range.append(False)
                        if any(check_range):
                            print(
                                f"bus_number : {new_stop.get('bus_number')} has no new stop that is not in the range of {self.config_Data['geofence_radius']} meters from the previous stops."
                            )
                            print("Yeh nahi hoga")
                            time.sleep(5)
                            pass
                        else:
                            new_records.append(new_stop)
                    else:
                        print("new_stop was None")
                if len(new_records) > 0:
                    print(check_range)
                    predicted_stops = self.load_stop(new_records, api_type)
                    print("CREATED STOP ID'S:", predicted_stops)
                    # with open(
                    #   "/home/ubuntu/prediction_dashboard_ambar/bus_stop/log_text.txt",
                    #    "w+",
                    # ) as file:
                    #   file.write(f"{check_range} *********** \n\n {new_records}")
                    print("Created")
                    self.compare_ab_stop(predicted_stops)
                else:
                    print("NO NEW STOPS CREATED.")
            else:
                print("new_ab_stops were None")
        except Exception as e:
            print(e)

    def auto_attach_stop(self, new_stop, distance=None):
        if distance == None:
            distance = D(m=self.config_Data["geofence_radius"])
        for id in new_stop:
            try:
                predict_stop = PredictedStop.objects.get(id=id)
                point = convertToPoint(predict_stop.longitude, predict_stop.latitude)
            except PredictedStop.DoesNotExist:
                predict_stop = None
            distance = self.distance_to_decimal_degrees(
                distance, predict_stop.longitude
            )

            if predict_stop is not None:
                try:
                    status_obj = StopStatus.objects.get(status_name="auto_attached")
                    bus_stop = (
                        BusStop.objects.filter(geofence_area__dwithin=(point, distance))
                        .order_by("geofence_area")
                        .first()
                    )
                except bus_stop.DoesNotExist:
                    print("No Nearest Stop Found For PREDICTED STOP")

                predict_stop.status = status_obj
                predict_stop.bus_stop = bus_stop
                predict_stop.stop_name = bus_stop.name
                predict_stop.town_id = bus_stop.town_id
                predict_stop.town_name = bus_stop.town_name
                predict_stop.save()




def convertToPoint(lat, lng):
    pnt = Point(lat, lng)
    pnt.srid = 4326
    return pnt





def create_new_stops():
    """
    Author: Ambar
    This function creates new bus stops by performing the following steps:

    1. Initializes a BusStatusCheck object (b_obj).
    2. Retrieves the list of bus numbers (that do not have any record with "created" status) using the checkStatus method.
    3. Retrieves the current date and time (today) and calculates the date
       three days ago (three_days_back) and change them to str from datetime.
    4. Iterates through each bus number in the list and performs the following actions:
       a. Prints the bus number.
       b. Initializes a BusStopsUtils object (bs_u) with the bus number and the date range
          from three_days_back to today.
       c. Calls the compare_mp_stop and compare_ab_stop methods of bs_u to compare and
          create new bus stops.

    This function is responsible for managing the creation of new bus stops based on
    the below criteria for each bus number:
        -> The new_mp_stops and new_ab_stops are not in the range of config(decided) range.

    Note: Ensure that the necessary classes and dependencies, such as BusStatusCheck and
    BusStopsUtils, are properly defined and imported in your code.

    PSEUDOCODE:
    FUNCTION create_new_stops()
    Author: Ambar
    Initialize b_obj as BusStatusCheck
    bus_list = b_obj.checkStatus()
    today = current_date_and_time
    three_days_back = calculate_three_days_back(today)

    FOR each bus_number IN bus_list
        PRINT bus_number
        bs_u = initialize BusStopsUtils with bus_number, three_days_back, and today
        bs_u.compare_mp_stop()
        bs_u.compare_ab_stop()
        PRINT "DONE"

    PRINT "Process Completed!"
    END FUNCTION

    FUNCTION calculate_three_days_back(current_date)
        three_days_ago = subtract 3 days from current_date
        three_days_ago = format three_days_ago as a string in "YYYY-MM-DD" format
        RETURN three_days_ago
    END FUNCTION

    """
    b_obj = BusStatusCheck()
    bus_list = b_obj.checkStatus()
    today = datetime.datetime.now()
    two_days_back = today - datetime.timedelta(days=2)
    two_days_back = datetime.datetime.strptime(
        str(two_days_back), "%Y-%m-%d %H:%M:%S.%f"
    )
    today = today.strftime("%Y-%m-%d")
    two_days_back = two_days_back.strftime("%Y-%m-%d")
    for bus_number in bus_list:
        print(bus_number)
        bs_u = BusStopsUtils(bus_number, two_days_back, today)
        bs_u.compare_mp_stop()
        bs_u.compare_ab_stop()
        print("DONE")
    print("Process Completed!")