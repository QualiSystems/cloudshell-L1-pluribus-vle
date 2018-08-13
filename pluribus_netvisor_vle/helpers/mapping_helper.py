class MappingHelpers(object):
    @staticmethod
    def parse_ports(ports):
        port_list = []
        single_records = ports.split(',')
        for record in single_records:
            if '-' in record:
                start, end = map(int, record.split("-"))
                range_list = map(str, range(start, end + 1))
            else:
                range_list = [record]
            port_list.extend(range_list)
        return port_list
