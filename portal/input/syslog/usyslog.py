import os
from cffi import FFI

ffi = FFI()
ffi.cdef("""
// Type definitions
typedef struct pbuffer pbuffer;
typedef struct syslog_parser syslog_parser;
typedef struct syslog_msg_head syslog_msg_head;
typedef struct syslog_parser_settings syslog_parser_settings;

typedef int (*syslog_cb) (syslog_parser *parser);
typedef int (*syslog_data_cb) (syslog_parser *parser, const char *at, size_t len);

// Structs
struct pbuffer {
    char *bytes;
    size_t position;
    size_t size;
};

struct syslog_msg_head {
    // Numeric Fields
    unsigned short priority;
    unsigned short version;

    // String Fields
    char *timestamp;
    size_t timestamp_len;

    char *hostname;
    size_t hostname_len;

    char *appname;
    size_t appname_len;

    char *processid;
    size_t processid_len;

    char *messageid;
    size_t messageid_len;
};

struct syslog_parser_settings {
    syslog_cb         on_msg_begin;
    syslog_cb         on_msg_head;
    syslog_data_cb    on_sd_element;
    syslog_data_cb    on_sd_field;
    syslog_data_cb    on_sd_value;
    syslog_data_cb    on_msg;
    syslog_cb         on_msg_complete;
};

struct syslog_parser {
    // Parser fields
    unsigned char flags : 3;
    unsigned char token_state;
    unsigned char state;

    // Error
    unsigned char error;

    // Message head
    struct syslog_msg_head *msg_head;

    // Byte tracking fields
    uint64_t message_length;
    uint64_t remaining;

    // Buffer
    pbuffer *buffer;

    // Optionally settable application data pointer
    void *app_data;
};

// Functions
void uslg_parser_reset(syslog_parser *parser);
void uslg_free_parser(syslog_parser *parser);

int uslg_parser_init(syslog_parser *parser, void *app_data);
int uslg_parser_exec(syslog_parser *parser, const syslog_parser_settings *settings, const char *data, size_t length);
""")

lib = ffi.verify(
    """
    #include "usyslog.h"
    """,
    include_dirs=['./include'],
    sources=['./include/usyslog.c'],
    extra_compile_args=['-D DEBUG_OUTPUT'])


class SyslogError(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class UnknownTypeError(SyslogError):

    def __init__(self, msg):
        super(UnknownTypeError, self).__init__(msg)


class ParsingError(SyslogError):

    def __init__(self, msg):
        super(ParsingError, self).__init__(msg)


class MessageHandlerError(SyslogError):

    def __init__(self, msg, cause):
        super(MessageHandlerError, self).__init__(msg)
        self.cause = cause

    def __str__(self):
        return 'MessageHandler exception: {} - {}'.format(
            self.msg, self.cause)


class SyslogMessageHandler(object):

    def message_head(self, message_head):
        pass

    def message_part(self, message_part):
        pass

    def message_complete(self, message_part):
        pass


class SyslogMessageHead(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self.priority = ''
        self.version = ''
        self.timestamp = ''
        self.hostname = ''
        self.appname = ''
        self.processid = ''
        self.messageid = ''
        self.sd = dict()
        self.current_sde = None
        self.current_sd_field = None

    def get_sd(self, name):
        return self.sd.get(name)

    def create_sde(self, sd_name):
        self.current_sde = dict()
        self.sd[sd_name] = self.current_sde

    def set_sd_field(self, sd_fieldname):
        self.current_sd_field = sd_fieldname

    def set_sd_value(self, value):
        self.current_sde[self.current_sd_field] = value

    def as_dict(self):
        sd_copy = dict()
        dictionary = {
            'priority': str(self.priority),
            'version': str(self.version),
            'timestamp': str(self.timestamp),
            'hostname': str(self.hostname),
            'appname': str(self.appname),
            'processid': str(self.processid),
            'messageid': str(self.messageid),
            'sd': sd_copy
        }

        for sd_name in self.sd:
            sd_copy[sd_name] = dict()
            for sd_fieldname in self.sd[sd_name]:
                sd_copy[sd_name][sd_fieldname] = self.sd[
                    sd_name][sd_fieldname].decode('utf-8')
        return dictionary


@ffi.callback("int (syslog_parser *parser)")
def on_msg_begin(parser):
    print('on_msg_begin')
    return 0

@ffi.callback("int (syslog_parser *parser)")
def on_msg_head(parser):
    print('on_msg_head')
    msg_head = ffi.from_handle(parser.app_data)
    print(msg_head)

    msg_head.priority = parser.msg_head.priority
    msg_head.version = parser.msg_head.version
    msg_head.timestamp = ffi.string(
        parser.msg_head.timestamp,
        parser.msg_head.timestamp_len)
    msg_head.hostname = ffi.string(
        parser.msg_head.hostname,
        parser.msg_head.hostname_len)
    msg_head.appname = ffi.string(
        parser.msg_head.appname,
        parser.msg_head.appname_len)
    msg_head.processid = ffi.string(
        parser.msg_head.processid,
        parser.msg_head.processid_len)
    msg_head.messageid = ffi.string(
        parser.msg_head.messageid,
        parser.msg_head.messageid_len)

    print(msg_head.priority)
    print(msg_head.version)
    print(msg_head.timestamp)
    print(msg_head.hostname)
    print(msg_head.appname)
    print(msg_head.processid)
    print(msg_head.messageid)

    return 0

@ffi.callback("int (syslog_parser *parser, const char *at, size_t len)")
def on_sd_element(parser, at, size):
    print('on_sd_element')
    return 0

@ffi.callback("int (syslog_parser *parser, const char *at, size_t len)")
def on_sd_field(parser, at, size):
    print('on_sd_field')
    return 0

@ffi.callback("int (syslog_parser *parser, const char *at, size_t len)")
def on_sd_value(parser, at, size):
    print('on_sd_value')
    return 0

@ffi.callback("int (syslog_parser *parser, const char *at, size_t len)")
def on_msg(parser, at, size):
    print('on_msg')
    return 0

@ffi.callback("int (syslog_parser *parser)")
def on_msg_complete(parser):
    print('on_msg_complete')
    return 0



class Parser(object):

    def __init__(self, msg_delegate):
        self._msg_head = SyslogMessageHead()
        self._msg_head_ctype = ffi.new_handle(self._msg_head)

        # Init the parser
        self._cparser = ffi.new("syslog_parser *")
        lib.uslg_parser_init(self._cparser, self._msg_head_ctype)

        # Init our callbacks
        self._cparser_settings = ffi.new("syslog_parser_settings *")
        self._cparser_settings.on_msg_begin = on_msg_begin
        self._cparser_settings.on_msg_head = on_msg_head
        self._cparser_settings.on_sd_element = on_sd_element
        self._cparser_settings.on_sd_field = on_sd_field
        self._cparser_settings.on_sd_value = on_sd_value
        self._cparser_settings.on_msg = on_msg
        self._cparser_settings.on_msg_complete = on_msg_complete


    def read(self, bytearray):
        lib.uslg_parser_exec(
            self._cparser,
            self._cparser_settings,
            bytearray,
            len(bytearray))

    def reset(self):
        self.cparser.reset()
