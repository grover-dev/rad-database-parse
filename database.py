import sqlite3
from sqlite3 import Error


class Database:
    def __init__(self, path):
        self.conn = None
        self.cursor = None
        try:
            self.conn = sqlite3.connect(path)
            self.cursor = self.conn.cursor()
        except Error as e:
            print(e)

    def close_conn(self):
        self.cursor.close()

    def add_entry_to_table(self, table, keys, values):
        if not self.check_if_exists(table,keys,values):

            key_str = "("
            value_str = "("
            for k, v in zip(keys, values):
                key_str += f"{k},"
                value_str += f"'{v}',"
            key_str = key_str[0:len(key_str)-1]
            value_str = value_str[0:len(value_str)-1]
            value_str = value_str.replace("\n"," ")
            entry = f""" INSERT INTO {table} {key_str}) VALUES {value_str});"""

            self.cursor.execute(entry)
            self.conn.commit()


    def add_to_entry_in_table(self, table, id_key, id_value, keys, values): 
        key_str = ""
        for k, v in zip(keys, values):
            key_str += f"{k} = {v},\n"
        key_str = key_str[0:len(key_str)-2]+")\n"
        entry = f""" UPDATE {table} SET {key_str} WHERE {id_key} = {id_value};"""
        self.cursor.execute(entry)

    def check_if_exists(self, table, id_key, id_value):
        if type(id_key) != list:
            id_key = [id_key]
        if type(id_value) !=  list:
            id_value = [id_value]
        entry =""
        if len(id_key) > 1:
            tmp = ""
            for key, value in zip(id_key, id_value):
                tmp_value = value.replace("\"","").replace("\'","")
                tmp += f"{key} = \"{tmp_value}\"\nAND "
            tmp = tmp [:len(tmp)-4]
            entry = f"SELECT EXISTS(SELECT 1 FROM {table} WHERE {tmp} LIMIT 1);"            
        else:
            entry = f"SELECT EXISTS(SELECT 1 FROM {table} WHERE {id_key[0]} = \"{id_value[0]}\" LIMIT 1);"            

        if self.cursor.execute(entry).fetchone()[0] == 0 or self.cursor.execute(entry).fetchone()[0] == None:
            return False
        return True

        


    def delete_entry_from_table(self, table, id_key, id_value, limit=1):
        if limit == None:   
            entry = f""" DELETE FROM {table} WHERE {id_key} = {id_value};"""
        else:   
            entry = f""" DELETE FROM {table} WHERE {id_key} = {id_value} LIMIT {limit};"""
        self.cursor.execute(entry)



    def create_tables(self):
        cursor = self.cursor
        paper_table = """ CREATE TABLE IF NOT EXISTS paper_table (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        paper_name VARCHAR(1024)                      
                    );"""
        cursor.execute(paper_table)

        rad_table = """ CREATE TABLE IF NOT EXISTS rad_table (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        part_number VARCHAR(255) NOT NULL, 
                        manufacturer VARCHAR(255) NOT NULL,
                        tester_id VARCHAR(255),
                        device_function VARCHAR(255) NOT NULL,
                        category VARCHAR(255),
                        technology VARCHAR(255),
                        principal_investigator VARCHAR(255),
                        results VARCHAR(1024) NOT NULL,
                        spec BOOL,
                        dose_rate VARCHAR(255),
                        proton_energy VARCHAR(255),
                        degradation_level VARCHAR(255),
                        proton_fluence VARCHAR(255),
                        misc_info VARCHAR(1024),
                        source_paper INTEGER NOT NULL
                        ); """
                        # source_paper_year INTEGER NOT NULL


        cursor.execute(rad_table)

        # holds info on all abbreviations that are used in the documents 
        # type specifies whether the abbreviation is for a term or for a principal investigator
        abbreviation_table = """ CREATE TABLE IF NOT EXISTS abbreviation_table (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            abbreviation VARCHAR(255) NOT NULL,
                            expansion VARCHAR(255) NOT NULL,
                            type VARCHAR(255) NOT NULL,
                            source_papers VARCHAR(1024) NOT NULL
                            ); """
        cursor.execute(abbreviation_table)
        
        op_amp_specific_fields = """
                            number_of_channels VARCHAR(255),
                            slew_rate VARCHAR(255),
                            gbw VARCHAR(255),
                            three_db_bw VARCHAR(255),
                            psrr VARCHAR(255),
                            cmrr VARCHAR(255),
                            bias_current VARCHAR(255),
                            input_offset_voltage VARCHAR(255)
                             """

        memory_specific_fields = """
                            memory_format VARCHAR(255),
                            memory_size VARCHAR(255),
                            memory_interface VARCHAR(255),
                            clock_frequency VARCHAR(255),
                            write_cycle_time VARCHAR(255),
                            access_time VARCHAR(255)
                            """
        
        """
        ========================== transistor fields ==========================
        common values:
            device_type specifies fet/bjt/igbt
            cont current 
              bjts/igbt:  cont collector current
              mosfets/jfets: cont drain current
            
            break down voltage
              bjts; collector-emitter breakdown voltage
              mosfets/jfets: drain-source breakdown voltage
            gate charge
              only for mosfets/jfets/igbts
        bjt/igbt (igbt also includes gate charge)- specific: 
          ce saturation_voltage 
          dc_current_gain
        mosfet/jfet - specific:
          gs_threshold_voltage
          gc_max_voltage
          rds_on 
          input_capacitance
        """
        transistor_specific_fields = """
                            continuous_current VARCHAR(255),
                            break_down_volage VARCHAR(255), 
                            power VARCHAR(255),
                            gate_charge VARCHAR(255),

                            ce_saturation_voltage VARCHAR(255),
                            dc_current_gain VARCHAR(255),

                            gc_threshold_voltage VARCHAR(255),
                            gc_max_voltage VARCHAR(255),
                            rds_on VARCHAR(255),
                            input_capacitance VARCHAR(255)
                            """
        
        """
        ========================== voltage reference fields ==========================
        low_freq_noise - 0.1 Hz - 10 Hz noise
        high_freq_noise - 10 Hz - 10 kHz noise
        voltage_min/max - used for adjustable references (see device_type field)
        """
        voltage_ref_specific_fields = """
                            voltage_output_min VARCHAR(255),
                            voltage_output_max VARCHAR(255), 
                            voltage_output_nom VARCHAR(255),
                            current_output VARCHAR(255),
                            tolerance VARCHAR(255),
                            temperature_coeff VARCHAR(255),
                            low_freq_noise VARCHAR(255),
                            high_freq_noise VARCHAR(255)
                             """
        
        """
        ========================== voltage regulator fields ==========================
        device_type covers buck/boost/ldo/etc.

        switching_freq - for buck/boost converters
        max_droput_voltage - for LDOs
        """
        voltage_reg_specific_fields = """
                            voltage_output_min VARCHAR(255),
                            voltage_output_max VARCHAR(255), 
                            channels VARCHAR(255),

                            switching_freq VARCHAR(255),

                            max_dropout_voltage VARCHAR(255),
                            quiescent_current VARCHAR(255),
                            psrr VARCHAR(255)
                             """
        
        """
        ========================== diode specific fields ==========================
        device_type covers zener/schottky/tvs/led/etc.

        """
        diode_specific_fields = """
                            zener_voltage VARCHAR(255),
                            tolerance VARCHAR(255), 
                            max_current VARCHAR(255),
                            power_max VARCHAR(255),

                            forward_voltage VARCHAR(255),
                            reverse_voltage VARCHAR(255)
                             """
        """
        ========================== adc specific fields ==========================
        device_type covers zener/schottky/tvs/led/etc.

        """
        # adc_specific_fields = """
        #                     zener_voltage VARCHAR(255),
        #                     tolerance VARCHAR(255), 
        #                     max_current VARCHAR(255),
        #                     power_max VARCHAR(255),

        #                     forward_voltage VARCHAR(255),
        #                     reverse_voltage VARCHAR(255),
        #                 ); """
        
        # todo: optocoupler, photodiode, adc, dac, micrcontroller, schmitt triggers, uart/canbus/other transceivers, 
        # single board computer, image sensor, hall effect sensor, 


        category = [["operational_amplifiers", op_amp_specific_fields], 
                    ["memory", memory_specific_fields], 
                    ["transistors", transistor_specific_fields], 
                    ["voltage_references", voltage_ref_specific_fields], 
                    ["voltage_regulators", voltage_reg_specific_fields],
                    ["diodes", diode_specific_fields],
                    # ["adc", adc_specific_fields],
                    ]




        for cat in category:
            base_table = f""" CREATE TABLE IF NOT EXISTS {cat[0]} (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                part_number VARCHAR(255) NOT NULL,
                                part_family VARCHAR(255), 
                                part_family_id INTEGER,
                                manufacturer VARCHAR(255) NOT NULL,
                                device_type VARCHAR(255) NOT NULL,
                                technology VARCHAR(255),
            
                                supply_current VARCHAR(255),
                                current_per_channel VARCHAR(255),
                                voltage_supply_min VARCHAR(255),
                                voltage_supply_max VARCHAR(255),
                                temperature_range VARCHAR(255),
                                mounting_type VARCHAR(255),
                                package VARCHAR(255),
                                datasheet VARCHAR(255) NOT NULL,
                                rad_id INTEGER NOT NULL,
                                {cat[1]}
                            ); """

            cursor.execute(base_table)