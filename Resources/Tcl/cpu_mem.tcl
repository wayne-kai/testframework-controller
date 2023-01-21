puts "PID: [pid]"

# configurable parameters
set cpuDutyCycle 0.4
set memUsagePercent 0.3

# optional parameters
set period 5
set maxRuntime 120
set chunkSize 1000

puts "Target CPU usage: [expr 100 * $cpuDutyCycle]\%"

proc GetMemoryInfo {memoryType} {

	set regexFilter [subst {^ *$memoryType +(\[0-9A-F\]+)+}]

	set memInfo [exec "show memory statistics | include $regexFilter"]

	regexp { *([^ ]+) +([^$]+)$} $memInfo match type values

	set fields [concat $values]
	set titles [list head total used free lowest largest]

	foreach f $fields t $titles {
		array set mem_details [list $t $f]
	}
	
	return [array get mem_details]
}

proc GetProcMemoryHeld {} {
	
	set memInfo [exec "sh proc mem [pid] | inc Total"]
	
	regexp {^[^\d]+(\d+)\s*bytes\s*$} $memInfo match totalHeld
	
	return $totalHeld
}


set dutyIntervalSec [expr int($period * $cpuDutyCycle)]

array set memDetails [GetMemoryInfo Processor]
set targetMemUsed [expr int($memDetails(total) * $memUsagePercent)]
puts "Target memory usage: $targetMemUsed ([expr 100 * $memUsagePercent]\%)"

# seed value for buffer
set buffer [format "%#016x" 1]

# expand buffer to target memory usage
array set memDetails [GetMemoryInfo Processor]
while {$memDetails(used) < $targetMemUsed} {
	for {set i 0} {$i < $chunkSize} {incr i} {
		lappend buffer [format "%#016x" [expr [lindex $buffer end] + 1]]
	}
	
	array set memDetails [GetMemoryInfo Processor]
	puts "Total memory: $memDetails(total), Used memory: $memDetails(used), Free memory: $memDetails(free)"
}

puts "Total memory: $memDetails(total), Used memory: $memDetails(used), Free memory: $memDetails(free)"

set dummy 1
puts "Running..."
set runStart [clock seconds]
set currIntervalStart $runStart

# main program loop that runs until program exits
while {1} {
	set clkSec [clock seconds]

	# exceed max run time, terminate loop
	if {$maxRuntime < [expr $clkSec - $runStart]} {
		break
	}
	
	# decide whether to pause the program
	set secElapsed [expr [clock seconds] - $currIntervalStart]
	if {[expr $secElapsed < $dutyIntervalSec]} {
		incr dummy
	} else {
		after [expr ($period - $secElapsed) * 1000] 
		update
		set currIntervalStart [clock seconds]
		array set memDetails [GetMemoryInfo Processor]
		puts "Total memory: $memDetails(total), Used memory: $memDetails(used), Free memory: $memDetails(free)"
		puts "Memory held by process ([pid]): [GetProcMemoryHeld]"
	}	
}