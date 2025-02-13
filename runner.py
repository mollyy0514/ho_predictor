from mobile_insight.monitor import OnlineMonitor
from actor import Actor
from predictor import *
from actor import *
from feature_extractor import FeatureExtractor
from utils.loop_timer import LoopTimer
from threading import Thread
import os
import json
import argparse
from datetime import datetime as dt
import datetime
from predictor import Predictor
from utils.myMsgLogger import MyMsgLogger


def get_ser(folder, dev: str):
    d2s_path = os.path.join(folder, "device_setting.json")
    with open(d2s_path, "r") as f:
        device_to_serial = json.load(f)
        if dev.startswith("sm"):
            return os.path.join(
                "/dev/serial/by-id",
                f"usb-SAMSUNG_SAMSUNG_Android_{device_to_serial[dev]}-if00-port0",
            )
        elif dev.startswith("qc"):
            return os.path.join(
                "/dev/serial/by-id",
                f"usb-Quectel_RM500Q-GL_{device_to_serial[dev]}-if00-port0",
            )
        else:
            return("/tmp/ttyV1")


class Runner:
    def __init__(
        self,
        feature_extractor: FeatureExtractor,
        predictor: Predictor,
        actor: Actor,
        dev: str,
        ser: str,
        log_dir: str = None,
        baudrate=9600,
        predict_interval: float = 1.0,
    ) -> None:
        # Setup mobileinsight online monitor
        self.src = OnlineMonitor()
        self.src.set_serial_port(ser)
        self.src.set_baudrate(baudrate)

        self.feature_extractor = feature_extractor
        self.feature_extractor.set_source(self.src)
        self.predictor = predictor
        self.actor = actor

        self.pred_task = LoopTimer(predict_interval, self.predict_task)
        self.main_task = Thread(target=self.run_task, daemon=True)

        self.log_dir = self.create_log_dir(log_dir)
        self.fs = open(f'{self.log_dir}/{dev}_out.txt','a')
        self.fs.write("Timestamp,dev,prob\n")
        # now = dt.today()
        now = dt.datetime.today()
        n = [
            now.year,
            now.month,
            now.day,
            now.hour,
            now.minute,
            now.second,
        ]
        n = [str(x).zfill(2) for x in n]
        n = "-".join(n[:3]) + "_" + "-".join(n[3:])
        self.mi2log_log_path = os.path.join(
            self.log_dir, "mi2log",
            # "diag_log_{}_{}.mi2log".format(ser.replace('/','_'), os.path.basename(self.log_dir)),
            "diag_log_{}_{}.mi2log".format(dev, os.path.basename(n)),
        )
        self.xml_log_path = os.path.join(
            self.log_dir, "mi2log_xml",
            # "diag_log_{}_{}.xml".format(ser.replace('/','_'), os.path.basename(self.log_dir)),
            "diag_log_{}_{}.xml".format(dev, os.path.basename(n)),
        )

        dumper = MyMsgLogger()
        dumper.set_source(self.src)
        dumper.set_decoding(MyMsgLogger.XML)  # decode the message as xml
        dumper.set_dump_type(MyMsgLogger.FILE_ONLY)
        dumper.save_decoded_msg_as(self.xml_log_path)
        self.src.save_log_as(self.mi2log_log_path)

        self.ser = ser
        self.dev = dev
        self.ho_info = []
        
    def create_log_dir(self, log_dir):
        if log_dir is None:
            # now = dt.today()
            now = dt.datetime.today()
            n = [
                now.year,
                now.month,
                now.day,
                now.hour,
                now.minute,
                now.second,
            ]
            n = [str(x).zfill(2) for x in n]
            n = "-".join(n[:3]) + "_" + "-".join(n[3:])
            os.umask(0)
            # log_dir = os.path.join(os.path.dirname(__file__), "log", str(n))
            log_dir = os.path.join("/home/wmnlab/Desktop/experiment_log", str(n[:10]))
            print(log_dir)
        try:
            os.makedirs(log_dir, exist_ok=True)
            os.makedirs(os.path.join(log_dir, "mi2log"), exist_ok=True)
            os.makedirs(os.path.join(log_dir, "mi2log_xml"), exist_ok=True)
        except:
            print("no")
            exit(0)
        return log_dir

    def run(self):
        self.pred_task.start()
        self.feature_extractor.run()
        print('task running', flush=True)
        self.src.run()

    def run_task(self):
        self.src.run()

    def predict_task(self):
        x_in = self.feature_extractor.get_feature_dict()
        # RLF prediction
        pred_output = self.predictor.predict(self.fs, self.dev, x_in)
        # Timely RLF event (ho_keys & ho_info can be extend)
        now = dt.datetime.today()
        ho_keys = ['RLF', 'SN_setup', 'MN_HO', 'SN_HO']
        if self.ho_info != [] and (now - dt.datetime.strptime(self.ho_info[1], "%Y-%m-%d %H:%M:%S.%f")) > datetime.timedelta(seconds=3):
            self.ho_info = []
        for i, data in enumerate(list(x_in)):
            for key in ho_keys:
                if data[key]:
                    self.ho_info = [key, now.strftime("%Y-%m-%d %H:%M:%S.%f")]
                    self.actor.do_action(self.dev, pred_output, self.ho_info)
        # # RLF prediction
        # pred_output = self.predictor.predict(self.fs, self.dev, x_in)
        self.actor.do_action(self.dev, pred_output, self.ho_info)

class DefaultRunner(Runner):
    def __init__(
        self,
        dev: str,
        ser: str,
        # verbose: float,
        feature_extractor: FeatureExtractor,
        log_dir: str = None,
        baudrate=9600,
        predict_interval: float = 1,
        predictor: Predictor = Predictor(),
        actor: Actor = Actor(),
    ) -> None:
        super().__init__(
            feature_extractor,
            predictor,
            actor,
            args.dev,
            ser,
            log_dir,
            baudrate,
            predict_interval,
        )

        # verbose = min(verbose, 0.1)

        # self.verbose_task = LoopTimer(predict_interval, self.predict_task)

if __name__ == "__main__":
    from parser import *
    from extractor import *
    from feature_extractor import *
    from predictor.rlf_xgboost_predictor import RLF_Xgboost_Predictor
    
    parser = argparse.ArgumentParser(description="A script with a -d parameter.")
    parser.add_argument('-d', '--dev', required=True, help="device name")
    args = parser.parse_args()
    
    rrc_ota_parser = RRC_OTA_Parser()
    lte_ss_parser = Lte_Signal_Strength_Parser()
    nr_ss_parser = NR_Signal_Strength_Parser()

    ho_extractor = HO_Extractor(args.dev)
    ho_extractor.set_source_parser(rrc_ota_parser)

    mr_extractor = MR_Extractor(args.dev)
    mr_extractor.set_source_parser(rrc_ota_parser)

    lte_ss_extractor = Lte_Signal_Strength_Extractor(args.dev)
    lte_ss_extractor.set_source_parser(lte_ss_parser)

    nr_ss_extractor = NR_Signal_Strength_Extractor(args.dev)
    nr_ss_extractor.set_source_parser(nr_ss_parser)

    feature_extractor = FeatureExtractor(sample_interval_sec=0.1, sample_length_sec = 3)
    feature_extractor.add_parser(rrc_ota_parser)
    feature_extractor.add_parser(lte_ss_parser)
    feature_extractor.add_parser(nr_ss_parser)
    feature_extractor.add_extractor(ho_extractor)
    feature_extractor.add_extractor(mr_extractor)
    feature_extractor.add_extractor(lte_ss_extractor)
    feature_extractor.add_extractor(nr_ss_extractor)

    feature_extractor.set_data_order(
        [
            "LTE_HO",
            "MN_HO",
            "SN_setup",
            "SN_Rel",
            "SN_HO",
            "Conn_Req",
            "RLF",
            "SCG_RLF",
            "eventA1",
            "eventA2",
            "E-UTRAN-eventA3",
            "eventA5",
            "eventA6",
            "NR-eventA3",
            "eventB1-NR-r15",
            "reportCGI",
            "reportStrongestCells",
            "others",
            "nr_best_rsrq",
            "nr_best_rsrp",
            "lte_best_rsrq",
            "lte_best_rsrp",
            "current_nr_rsrq",
            "current_nr_rsrp",
            "current_lte_rsrq",
            "current_lte_rsrp",
            "scell1_lte_rsrq",
            "scell1_lte_rsrp",
            "scell2_lte_rsrq",
            "scell2_lte_rsrp",
            "scell3_lte_rsrq",
            "scell3_lte_rsrp",
            "lte_phy_EARFCN",
            "lte_phy_Number_of_Neighbor_Cells",
            "nr_phy_Num_Cells",
        ]
    )


    predictor = RLF_Xgboost_Predictor()
    runner = DefaultRunner(
        dev=args.dev,
        ser=get_ser(os.path.dirname(__file__), args.dev),
        predictor=predictor,
        feature_extractor=feature_extractor,
        predict_interval = 0.1,
        actor = TestActor()
    )

    try:
        runner.run()
        while True:
            time.sleep(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
