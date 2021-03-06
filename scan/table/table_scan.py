"""
Table Scan
==========

Creates a scan based on a table.

Basic Example
-------------

Each column of a table specifies a device name (Process Variable).
Cells in each row provide the desired values.

+-----------+---------+
|temperature|position |
+-----------+---------+
|   50      |   1     |
+-----------+---------+
|  100      |   2     |
+-----------+---------+

The table above creates the following scan commands::

   Set('temperature', 50),
   Set('position', 1),
   Set('temperature', 100),
   Set('position', 2),


Cells can remain empty if a device should not be changed in that row.

+-----------+---------+
|temperature|position |
+-----------+---------+
|   50      |   1     |
+-----------+---------+
|           |   2     |
+-----------+---------+
|           |   3     |
+-----------+---------+
|  100      |   1     |
+-----------+---------+
|           |   2     |
+-----------+---------+
|           |   3     |
+-----------+---------+

Results in::

   Set('temperature', 50),
   Set('position', 1),
   Set('position', 2),
   Set('position', 3),
   Set('temperature', 100),
   Set('position', 1),
   Set('position', 2),
   Set('position', 3),


Ranges, Lists
-------------

Cells that contain a `range()` command or list will be expanded,
resulting in this shorter version of the previous table:

+-----------+------------+
|temperature|position    |
+-----------+------------+
|   50      |range(1,4,1)|
+-----------+------------+
|  100      |[1, 2, 3]   |
+-----------+------------+

Within a row, multiple ranges or lists are recursively expanded from right to left.
This shorter table again results in the same scan commands:

+-----------+------------+
|temperature|position    |
+-----------+------------+
| [50,100]  | [1, 2, 3]  |
+-----------+------------+



Scan Settings
-------------

When for example accessing a 'position' device associtated with an EPICS motor,
the `Set` command should await completion,
then compare the 'position.RBV' against the desired position::

   Set('position', 2, completion=True, readback='position.RBV', tolerance=0.1)

The tolerance for this comparison as well as a timeout will depend on the actual
motor.

You may have a known list of device names and how they need to be accessed,
or you may be able to derive this information based on a naming standard for devices
at your site.

The :mod:`scan.util.scan_settings` module is used to configure how the
`TableScan` accesses devices.


Code Example
-------------

.. literalinclude:: ../example/table1.py

'Wait For', 'Value', 'Or Time' Columns
--------------------------------------

These two columns create commands that wait for
a condition, and then log all devices which
have been used within the scan up to that point.

If the cell contains a device name,
a `Wait` command is created for the device to reach the given value.

+----------+------------+--------+
|position  |Wait For    |  Value |
+----------+------------+--------+
|  2       | counter    | 10000  |
+----------+------------+--------+

The table above will create the following scan::

    Set('position', 2.0, completion=true, readback='position.RBV', timeOut=100)
    Wait('counter', 10000.0, comparison='>=')
    Log('position', 'counter')

The :class:`~scan.util.scan_settings.ScanSettings` 
determine the detailed options of the `Set` and `Wait` commands.
By default, the generated `Wait` command will wait forever,
unless the `ScanSettings` provide a timeout.
In the example above, we assume that the `ScanSetting` cause every access
to the 'position' device to use completion and readback.

A prefix `-c` can disable the completion check:

+--------------+------------+--------+
|-c position   |Wait For    |  Value |
+--------------+------------+--------+
|  2           | counter    | 10000  |
+--------------+------------+--------+

Resulting scan without completion for the 'position'::

    Set('position', 2.0, readback='position.RBV', timeOut=100)
    Wait('counter', 10000.0, comparison='>=')
    Log('position', 'counter')

For more prefix options see :class:`~scan.util.scan_settings.ScanSettings`.


Waiting for `seconds` results in a simple `Delay`.

+----------+------------+--------+
|position  |Wait For    |  Value |
+----------+------------+--------+
|  2       | seconds    |   20   |
+----------+------------+--------+
|  4       | seconds    |   20   |
+----------+------------+--------+

The table above will create the following scan::

    Set('position', 2.0, completion=true, readback='position.RBV', timeOut=100)
    Delay(20)
    Log('position')
    Set('position', 4.0, completion=true, readback='position.RBV', timeOut=100)
    Delay(20)
    Log('position')

The delay is specified in seconds or a "HH:MM:SS" notation for hours, minutes, seconds.
The following rows are all equivalent:

+----------+------------+----------+
|position  |Wait For    |  Value   |
+----------+------------+----------+
|  1       | seconds    |      120 |
+----------+------------+----------+
|  1       | seconds    |    01:00 |
+----------+------------+----------+
|  1       | seconds    | 00:01:00 |
+----------+------------+----------+


A column 'Or Time' can be added to allow the scan to continue even if the condition is **not** met:

+----------+------------+--------+----------+
|position  |Wait For    |  Value | Or Time  |
+----------+------------+--------+----------+
|  [2,4,7] | counter    | 10000  | 01:00:00 |
+----------+------------+--------+----------+

The scan generated by this table will set the 'position' to three different values.
At each step, it will wait until either the 'counter' reaches a value of 10000,
or one hour passes.


All devices with a `+p` prefix will be accessed in parallel,
awaiting completion before executing the 'Wait For' condition.

If there is no specific 'Wait For' condition, the cell can be set to
`completion`.

+------+------+------------+--------+
| +p x | +p y | Wait For   |  Value |
+------+------+------------+--------+
|  1   |   2  | counter    | 10000  |
+------+------+------------+--------+
|  3   |   4  | completion |   20   |
+------+------+------------+--------+

Result::

    Parallel(Set('x', 1.0), Set('y', 2.0))
    Wait('counter', 10000.0, comparison='>=')
    Log('x', 'y', 'counter')
    Parallel(Set('x', 3.0), Set('y', 4.0))
    Log('x', 'y', 'counter')


Log Additional Devices
----------------------

The example just shown ends in::
   
    Log('x', 'y', 'counter')

because all devices used in a row are logged upon completing the 'Wait For' condition.
These devices could have been affected by a column that set them to a value,
or the 'Wait For' condition depended on the device.

To log additional devices, even though they are otherwise not mentioned in the table,
pass the `log_always` parameter to the table::

    table = TableScan(headers, rows, log_always=[ 'neutrons' ])
    
will include the device `neutrons` whenever it logs values at the end of a row.


Pre, Post, Start and Stop Commands
----------------------------------

Both the devices listed in the table column headers
and the values used in the cells of the rows of the
table are typically edited for different runs of
an experiment.

There are, however, often the same actions that need
to happen before and after the complete table is executed,
as well as at each step of a table.

You can provide a list of commands for the following steps:

`pre`:
    Before executing the table rows.
    Example: Open a beam line shutter.

`post`:
    After executing all table rows.
    Example: Close a beam line shutter.

`start`:
    Before each 'Wait For'.
    Example: Zero counter PVs, in fact counters 
    which the 'Wait For' command will then check
    to reach a certain value, and start data acquisition.

`stop`:
    After each 'Wait For' completes.
    Example: Stop data acquisition.


Special Column handling
-----------------------

Going back to the most basic behavior of the table scan,
given a column name and a cell value, each non-empty cell
results in a command::

   Set(column_name, cell_value)

For example, a column named "RunControl" with cell values "start" and "stop":

+------------+
| RunControl |
+------------+
| start      |
+------------+
| stop       |
+------------+

would result in these commands::

   Set("RunControl", "start")
   Set("RunControl", "stop")

Assuming that the process variable "RunControl" is an enumerated type with valid states "start" and "stop",
maybe connected to an IOC sequence to start and stop a data acquisition run, this will work just fine.

Extending the example, assume that you would rather use "Run Control" as a column name to distinguish it from
an ordinary process variable, and the cell values should result in `Include` commands.

To handle such special cases, the `TableScan` API allows you to provide a dictionary with special column handler functions.
Each function is called with the value of the cell, and it must return a scan command.

Example::

   special_handlers = { 'Run Control': lambda cell : Include(cell + ".scn") }
   table_scan = TableScan(( "Run Control" ),
                         [[ "start"       ],
                          [ "stop"        ]
                         ], special = special_handlers)

When handling cells for the "Run Control" column, the special handler function
will now be invoked with the cell values, i.e. "start" and "stop"::
   
   lambda cell : Include(cell + ".scn")

resulting in these commands::

   Include("start.scn")
   Include("stop.scn")

The special handler function can wrap multiple commands as a :class:`~scan.commands.sequence.Sequence` command.


API
---
"""
# @author: Kay Kasemir

from scan.commands import Command, Comment, Delay, Log, Parallel
from scan.util.scan_settings import getScanSettings, SettingsBasedSet, SettingsBasedWait
from scan.util.seconds import parseSeconds
from range_helper import expandRanges
from scan.util.spreadsheet import readSpreadsheet, writeSpreadsheet

def loadTableScan(filename, pre=None, post=None, start=None, stop=None):
    """Load table from spreadsheet file
       
    :param filename:     File name, either '*.cvs', '*.tab', '*.xls' or '*.gnumeric'
    :param pre:          Command or list of commands executed at the start of the table.
    :param post:         Command or list of commands executed at the end of the table.
    :param start:        Command or list of commands executed to start each 'Wait For'.
    :param stop:         Command or list of commands executed at the end of each 'Wait For'.
    """
    table = readSpreadsheet(filename)
    headers = table[0]
    rows = table[1:]
    return TableScan(headers, rows, pre, post, start, stop)

class TableScan:
    """Create Table scan
    
    :param headers[]:    Column headers of the table
    :param rows[][]:     Rows of the scan. Each row must have len(headers) columns.
    :param pre:          Command or list of commands executed at the start of the table.
    :param post:         Command or list of commands executed at the end of the table.
    :param start:        Command or list of commands executed to start each 'Wait For'.
    :param stop:         Command or list of commands executed at the end of each 'Wait For'.
    :param log_always:   Optional list of device names that should be logged in addition
                         to those that are affected by columns that set them
                         or 'Wait For' conditions.
    :param special:      Dictionary with special column handlers
    """
    
    # Predefined columns
    COMMENT = "Comment"
    WAITFOR = "Wait For"
    VALUE = "Value"
    OR_TIME = "Or Time"
    COMPLETION = "completion"
    SECONDS = "seconds"
    
    def __init__(self, headers, rows, pre=None, post=None, start=None, stop=None, log_always=None, special=dict()):
        self.name = "Table Scan"
        self.pre = self.__makeList(pre)
        self.post = self.__makeList(post)
        self.start = self.__makeList(start)
        self.stop = self.__makeList(stop)
        self.special = special
        self.log_always=log_always
        # When called with table widget data,
        # values may be java.lang.String u'text'.
        # Convert to plain 'text'.
        #
        # In addition, measure the width of each column
        # and skip empty rows
        self.headers = [ str(h).strip() for h in headers ]
        self.cols = len(self.headers)
        self.rows = []
        self.width = [ len(h) for h in self.headers ]
        for row in rows:
            is_empty = True
            patched_row = []
            for c in range(len(row)):
                cell = row[c]
                patched = str(cell).strip()
                patched_row.append(patched)
                width = len(patched)
                if width > self.width[c]:
                    self.width[c] = width
                if width > 0:
                    is_empty = False
            if len(patched_row) != len(self.headers):
                raise ValueError("Not all rows have equal number of columns")
            if not is_empty:
                self.rows.append(patched_row)
    
    def save(self, filename):
        """Save table to file
    
        Writes table as CSV file.
    
        :param filename: File path, must end in ".csv" or ".tab"
        """
        table = [ self.headers ] + self.rows
        writeSpreadsheet(filename, table)

    def __makeList(self, cmd):
        if isinstance(cmd, Command):
            return [ cmd ]
        if cmd:
            return list(cmd)
        return None
    
    def __getValue(self, text):
        """Get value from text
           text: Text that may contain numeric value
           Returns Number or text.
        """ 
        try:
            return float(text)
        except ValueError:
            return text # Keep as string
    
    def createScan(self):
        """Create scan.
        
        :return: List of commands.
        """
        # Parse column headers.
        settings = getScanSettings()
        col_device = [ None for i in range(self.cols) ]
        i = 0
        while i < self.cols:
            if self.headers[i] == TableScan.WAITFOR:
                # Column TableScan.WAITFOR must be followed by TableScan.VALUE
                if i >= self.cols-1  or  self.headers[i+1] != TableScan.VALUE:
                    raise ValueError(TableScan.WAITFOR + " column must be followed by " + TableScan.VALUE)
                # .. and may then be followed by TableScan.OR_TIME
                if i < self.cols-2  and  self.headers[i+2] == TableScan.OR_TIME:
                    i += 2
                else:
                    i += 1
            elif self.headers[i] in ( TableScan.COMMENT ):
                # Ignore other special columns
                pass
            else:
                # Parse device info
                col_device[i] = settings.parseDeviceSettings(self.headers[i])
            i += 1
        
        # Expand any range(start, end, step) cells
        expanded_rows = expandRanges(self.rows)
        
        # Assemble commands for each row in the table
        commands = list()
        log_devices = list()
        if self.log_always is not None:
            log_devices = list(self.log_always)
        if self.pre:
            commands += self.pre
        line = 0
        for row in expanded_rows:
            line += 1
            # Parallel commands to execute in this row
            parallel_commands = list()
            # Handle all columns
            i = 0
            while i < self.cols:
                what = self.headers[i]
                if len(row[i]) <= 0:
                    pass # Empty column, nothing to do
                elif what in self.special:
                    special_handler = self.special[what]
                    value = self.__getValue(row[i])
                    command = special_handler(value)
                    commands.append(command)
                elif what == TableScan.COMMENT:
                    text = row[i]
                    commands.append(Comment(text))           
                    # TODO if self.settings.comment:
                    #       commands.append(SetCommand(self.settings.comment, text))
                elif what == TableScan.WAITFOR:
                    waitfor = row[i]
                    value = self.__getValue(row[i+1])

                    if waitfor.lower() != TableScan.COMPLETION  and  parallel_commands:
                        # Complete accumulated parallel_commands before starting the run
                        commands.append(Parallel(parallel_commands))
                        parallel_commands = list()

                    # Optional commands to mark start of a "Wait For"
                    if self.start:
                        commands += self.start

                    if waitfor.lower() == TableScan.COMPLETION:
                        # Assert that there are any parallel commands,
                        # because otherwise the 'WaitFor - Completion' was likely an error
                        if not parallel_commands:
                            raise Exception("Line %d has no parallel commands to complete" % line)
                        commands.append(Parallel(parallel_commands))
                        parallel_commands = list()
                    elif waitfor.lower() == TableScan.SECONDS:
                        if value:
                            commands.append(Delay(parseSeconds(value)))
                    else:
                        timeout = None
                        errhandler = None
                        if i+2 < self.cols  and  self.headers[i+2] == TableScan.OR_TIME:
                            or_time = row[i+2].strip()
                            if len(or_time) > 0:
                                timeout = parseSeconds(or_time)
                                errhandler = "OnErrorContinue"
                        cmd = SettingsBasedWait(waitfor, value, timeout=timeout, errhandler=errhandler)
                        commands.append(cmd)
                        if not waitfor in log_devices:
                            log_devices.append(waitfor)
                    
                    if len(log_devices) > 0:
                        commands.append(Log(log_devices))

                    # Optional commands to mark end of a "Wait For"
                    if self.stop:
                        commands += self.stop
                    
                    # Skip TableScan.VALUE in addition to current column,
                    # so next two Exceptions should not happen unless there's an empty "WAIT_FOR"
                    if i+2 < self.cols  and  self.headers[i+2] == TableScan.OR_TIME:
                        i = i + 2
                    else:
                        i = i + 1
                elif what == TableScan.VALUE:
                    raise Exception("Line %d: Found value '%s' in '%s' column after empty '%s' column.\nRow: %s" %
                                    (line, row[i], TableScan.VALUE, TableScan.WAITFOR, str(row)))
                elif what == TableScan.OR_TIME:
                    raise Exception("Line %d: Found value '%s' in '%s' column after empty '%s' column.\nRow: %s" %
                                    (line, row[i], TableScan.OR_TIME, TableScan.WAITFOR, str(row)))
                else:
                    # 'Normal' column that sets a device
                    device = col_device[i]
                    value = self.__getValue(row[i])
                    command = SettingsBasedSet(what, value)
                        
                    if device.getParallel():
                        parallel_commands.append(command)
                    else:
                        commands.append(command)
                    
                    if not device.getName() in log_devices:
                        log_devices.append(device.getName())
                i = i + 1
            # End of columns in row
            # Complete accumulated parallel commands
            if parallel_commands:
                commands.append(Parallel(parallel_commands))
                parallel_commands = list()
        
        if self.post:
            # End one long run at end of table
            commands += self.post
        
        return commands

        
    def __repr__(self):
        """Returns table as columnized string."""
        result = 'headers=[ "'
        line = []
        for c in range(self.cols):
            line.append(self.headers[c].ljust(self.width[c]))
        result += '", "'.join(line)
        result += '" ]\nrows= ['
        for row in self.rows:
            line = []
            for c in range(self.cols):
                line.append(row[c].ljust(self.width[c]))
            result += ' [ "' + '", "'.join(line) + '" ],\n       '
        result += "]"
        return result
    
